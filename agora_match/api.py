"""Production ASGI entry point. The existing UI and Azure API share one origin."""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import fastapi
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .catalog import build_catalog
from .projection import project_game, view_patch
from .chat import answer_question
from .config import AppSettings
from .narrator import FoundryNarrator
from .telemetry import configure_observability, event, span

STATIC = Path(__file__).resolve().parent.parent / "static"


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    role: Literal["user", "assistant"]
    content: str = Field(max_length=1000)


class Ask(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=1000)
    persona: Literal["fan", "analyst", "coach"] = "fan"
    game_id: str = Field(default="northbridge-eastport", max_length=80)
    player_id: str | None = Field(default=None, max_length=32)
    simplify: bool = False
    analysis_time_seconds: int | None = Field(default=None, ge=0, le=7200)
    language: Literal["en", "el"] = "en"
    conversation: list[Turn] = Field(default_factory=list, max_length=6)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("question is blank")
        return value


class Narration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    insight_id: str = Field(max_length=100)
    game_id: str = Field(default="northbridge-eastport", max_length=80)
    view: Literal["fan", "explorer", "studio", "analyst", "coach"] = "fan"
    simplify: bool = False
    analysis_time_seconds: int | None = Field(default=None, ge=0, le=7200)
    language: Literal["en", "el"] = "en"


class RequestWindow:
    def __init__(self, limit):
        self.limit, self.times, self.lock = limit, deque(), threading.Lock()

    def allow(self):
        with self.lock:
            now = time.monotonic()
            while self.times and now - self.times[0] >= 60:
                self.times.popleft()
            if len(self.times) >= self.limit:
                return False
            self.times.append(now)
            return True


def create_app(settings: AppSettings | None = None, narrator: FoundryNarrator | None = None,
               catalog: dict | None = None) -> fastapi.FastAPI:
    configure_observability()
    settings = settings or AppSettings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        app.state.catalog = catalog or build_catalog()
        app.state.narrator = narrator or FoundryNarrator(app_settings=settings)
        app.state.ready = bool(app.state.catalog.get("synthetic") and app.state.catalog.get("games"))
        event("application_started", mode=app.state.narrator.mode())
        yield
        app.state.ready = False
        app.state.narrator.close()

    app = fastapi.FastAPI(title="Agora Match API",version="1.0.0",lifespan=lifespan, docs_url=None,redoc_url=None)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=list(settings.allowed_hosts))
    request_window = RequestWindow(settings.api_requests_per_minute)

    @app.middleware("http")
    async def protect_and_measure(request, call_next):
        request_id = uuid.uuid4().hex
        start = time.monotonic()
        if request.method == "POST":
            if not request_window.allow():
                return JSONResponse({"error":"Too many requests. Try again shortly.","request_id":request_id},429,headers={"Retry-After":"60"})
            origin = request.headers.get("origin")
            if origin and (urlsplit(origin).scheme not in {"http","https"} or urlsplit(origin).netloc != request.headers.get("host")):
                return JSONResponse({"error":"Cross-origin requests are not enabled."},403)
            if request.headers.get("content-type","").split(";")[0].strip().lower() != "application/json":
                return JSONResponse({"error":"Content-Type must be application/json."},415)
            try:
                async with asyncio.timeout(5):
                    body = bytearray()
                    async for chunk in request.stream():
                        body.extend(chunk)
                        if len(body) > 16_000:
                            return JSONResponse({"error":"Request is too large."},413)
                request._body = bytes(body)
            except TimeoutError:
                return JSONResponse({"error":"Request body timed out."},408)
        try:
            with span("agora.http",request_id=request_id):
                response = await call_next(request)
        except Exception:
            event("request_failed",request_id=request_id,reason="internal_error")
            response = JSONResponse({"error":"The request could not be completed.","request_id":request_id},500)
        response.headers.update({
            "X-Request-ID":request_id,"X-Content-Type-Options":"nosniff","Referrer-Policy":"same-origin",
            "Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
            "Permissions-Policy":"camera=(), geolocation=()",
        })
        if request.url.path.startswith(("/api/","/health/")):
            response.headers["Cache-Control"] = "no-store"
        safe_path = request.url.path if request.url.path in {"/api/ask","/api/narrate","/health/live","/health/ready","/api/health","/api/state"} else "static_or_stream"
        event("http_request",request_id=request_id,path=safe_path,http_status=response.status_code,duration_ms=round((time.monotonic()-start)*1000))
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, exc):
        return JSONResponse({"error":"Invalid request fields.","fields":[".".join(map(str,e["loc"])) for e in exc.errors()]},422)

    def find_game(game_id, seconds=None):
        game = next((g for g in app.state.catalog["games"] if g["match"]["game_id"] == game_id),None)
        if game is None:
            raise fastapi.HTTPException(404,"Unknown game_id")
        try:
            return project_game(game,seconds) if seconds is not None else game
        except ValueError:
            raise fastapi.HTTPException(400,"Invalid analysis time") from None

    @app.get("/health/live")
    @app.get("/api/health")
    def live():
        return {"ok":True,"synthetic":True,"service":"agora-match"}

    @app.get("/health/ready")
    def ready():
        model = app.state.narrator
        ok = app.state.ready and not model.config.errors() and (not settings.require_ai or model.configured())
        return JSONResponse({"ready":ok,"data":"synthetic","ai":model.status()},200 if ok else 503)

    @app.get("/api/capabilities")
    def capabilities():
        return {"hosting":"azure_container_apps" if os.getenv("CONTAINER_APP_NAME") else "local_asgi",
                "data_mode":"synthetic_replay","ai":app.state.narrator.status(),
                "telemetry_configured":bool(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")),
                "stream":"resumable_sse","limits_scope":"per_process_per_replica"}

    @app.get("/api/games")
    def games():
        return {"synthetic":True,"games":[{"game_id":g["match"]["game_id"],"label":g["match"]["label"],"match":g["match"]} for g in app.state.catalog["games"]]}

    @app.get("/data/games.json")
    def data():
        return app.state.catalog

    @app.get("/api/analysis")
    def analysis(game_id: str = "northbridge-eastport", analysis_time_seconds: int | None = None):
        return view_patch(find_game(game_id,analysis_time_seconds))

    @app.get("/api/state")
    def state(game_id: str = "northbridge-eastport", view: str = "fan", analysis_time_seconds: int | None = None):
        internal = {"fan":"fan","analyst":"explorer","explorer":"explorer","coach":"studio","studio":"studio"}.get(view)
        if not internal:
            raise fastapi.HTTPException(400,"Invalid audience")
        game, model = find_game(game_id,analysis_time_seconds), app.state.narrator
        return {k:game[k] for k in ("match","players","events","attacks","tracking_snapshots","recap")} | {
            "view":view,"insights":[i | {"presentation":i[internal+"_summary"]} for i in game["insights"]],
            "foundry_configured":model.configured(),"foundry_mode":model.mode(),"foundry_status":model.status(),
        }

    @app.post("/api/ask")
    def ask(body: Ask):
        game = find_game(body.game_id,body.analysis_time_seconds)
        if body.player_id and not any(p["id"] == body.player_id for p in game["players"]):
            raise fastapi.HTTPException(404,"Unknown player_id")
        grounded = answer_question(game,body.question,body.persona,body.player_id,body.simplify,[t.model_dump() for t in body.conversation])
        grounded["language"] = body.language
        result = app.state.narrator.answer(body.question,body.persona,grounded,body.simplify)
        return result | {"data_mode":"synthetic","analysis_context":game["analysis_context"],"data_through_minute":game["match"]["minute"],"foundry_status":app.state.narrator.status()}

    @app.post("/api/narrate")
    def narrate(body: Narration):
        game = find_game(body.game_id,body.analysis_time_seconds)
        insight = next((i for i in game["insights"] if i["id"] == body.insight_id),None)
        if insight is None:
            raise fastapi.HTTPException(404,"Unknown insight_id")
        return app.state.narrator.narrate(insight,body.view,body.simplify,body.language)

    @app.get("/api/events/{game_id}")
    async def events(game_id: str, request: fastapi.Request, after: int = -1, speed: int = 2):
        game = find_game(game_id)
        if speed not in {1,2,4}:
            raise fastapi.HTTPException(400,"Invalid replay speed")
        ordered = sorted(game["events"],key=lambda e:(e["minute"],e["id"]))
        last_id = request.headers.get("last-event-id")
        if last_id is not None:
            try:
                after = int(last_id)
            except ValueError:
                raise fastapi.HTTPException(400,"Invalid Last-Event-ID") from None
        if not -1 <= after < len(ordered):
            raise fastapi.HTTPException(400,"Invalid event cursor")
        async def stream():
            for sequence in range(after+1,len(ordered)):
                if await request.is_disconnected():
                    return
                row = {"sequence":sequence,"data_mode":"synthetic_replay","event":ordered[sequence]}
                yield f"id: {sequence}\nevent: match_event\ndata: {json.dumps(row)}\n\n"
                await asyncio.sleep(.75 / speed)
            yield 'event: complete\ndata: {"data_mode":"synthetic_replay"}\n\n'
        return StreamingResponse(stream(),media_type="text/event-stream",headers={"X-Accel-Buffering":"no"})

    app.mount("/",StaticFiles(directory=STATIC,html=True),name="ui")
    return app
