"""Azure v1 model client: keyless identity, model profiles, admission and recovery."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import httpx

from .config import FoundrySettings


class ProviderError(Exception):
    """Only safe machine-readable codes cross the provider boundary."""
    def __init__(self, code: str, retryable: bool = False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


@dataclass
class Completion:
    text: str
    usage: dict[str, int]


class Admission:
    """Limits apply per process/replica; these are not a dollar spending cap."""
    def __init__(self, settings: FoundrySettings, clock=time.monotonic):
        self.settings, self.clock = settings, clock
        self.lock = threading.Lock()
        self.slots = threading.BoundedSemaphore(settings.max_concurrency)
        self.calls = deque()
        self.failures = 0
        self.opened_at = None
        self.probe = False

    def enter(self):
        if not self.slots.acquire(blocking=False):
            raise ProviderError("model_busy")
        try:
            with self.lock:
                now = self.clock()
                if self.opened_at is not None:
                    if now - self.opened_at < self.settings.circuit_cooldown or self.probe:
                        raise ProviderError("circuit_open")
                    self.probe = True
                while self.calls and now - self.calls[0] >= 60:
                    self.calls.popleft()
                if len(self.calls) >= self.settings.requests_per_minute:
                    self.probe = False
                    raise ProviderError("model_rate_limit")
                self.calls.append(now)
        except Exception:
            self.slots.release()
            raise

    def leave(self, success: bool):
        with self.lock:
            if success:
                self.failures, self.opened_at = 0, None
            else:
                self.failures += 1
                if self.probe or self.failures >= self.settings.circuit_failures:
                    self.opened_at = self.clock()
            self.probe = False
        self.slots.release()


class AzureModelClient:
    def __init__(self, settings: FoundrySettings, *, http: httpx.Client | None = None,
                 token_provider: Callable[[], str] | None = None, clock=time.monotonic, sleep=time.sleep):
        self.settings = settings
        self.http = http or httpx.Client(follow_redirects=False, limits=httpx.Limits(max_connections=8, max_keepalive_connections=4))
        self.token_provider = token_provider
        self.clock, self.sleep = clock, sleep
        self.admission = Admission(settings, clock)
        self._credential = None
        self._credential_lock = threading.Lock()
        self.last_success = None
        self.last_error = None

    def close(self):
        self.http.close()
        if self._credential is not None:
            self._credential.close()

    def _headers(self) -> dict[str, str]:
        if self.settings.identity_mode == "api_key":
            return {"api-key": self.settings.api_key}
        if self.token_provider:
            return {"Authorization": "Bearer " + self.token_provider()}
        try:
            with self._credential_lock:
                if self._credential is None:
                    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
                    self._credential = (ManagedIdentityCredential(client_id=self.settings.client_id)
                                        if self.settings.identity_mode == "managed_identity" else
                                        DefaultAzureCredential(exclude_interactive_browser_credential=True))
            token = self._credential.get_token(self.settings.token_scope)
            return {"Authorization": "Bearer " + token.token}
        except Exception:
            raise ProviderError("identity_unavailable") from None

    def complete(self, deployment: str, system: str, evidence: dict, max_tokens: int, deadline: float, *, response_schema: dict | None = None) -> Completion:
        import json
        reasoning = deployment in self.settings.reasoning_deployments
        payload = {
            "model": deployment,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)}],
        }
        if response_schema:
            payload['response_format'] = {'type': 'json_schema', 'json_schema': {
                'name': 'agora_response', 'strict': True, 'schema': response_schema}}
        if reasoning:
            payload["max_completion_tokens"] = max(1024, max_tokens * 4)
            if self.settings.reasoning_effort:
                payload["reasoning_effort"] = self.settings.reasoning_effort
        else:
            payload.update({"temperature": 0.1, "max_tokens": max_tokens})
        for attempt in range(2):
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise ProviderError("answer_deadline")
            self.admission.enter()
            success = False
            retry_delay = .2
            try:
                response = self.http.post(
                    self.settings.base_url + "/chat/completions", json=payload,
                    headers=self._headers(), timeout=min(self.settings.timeout_seconds, remaining),
                )
                if response.status_code != 200:
                    code = "provider_auth" if response.status_code in {401, 403} else "provider_configuration" if response.status_code in {400, 404} else "provider_throttled" if response.status_code == 429 else "provider_unavailable"
                    try:
                        retry_delay = min(1, max(.1, float(response.headers.get("retry-after", ".2"))))
                    except ValueError:
                        retry_delay = .2
                    raise ProviderError(code, response.status_code in {429, 502, 503, 504})
                body = response.json()
                choice = body["choices"][0]
                text = choice["message"]["content"]
                if choice.get("finish_reason") in {"length", "content_filter"} or not isinstance(text, str) or not text.strip():
                    raise ProviderError("provider_incomplete")
                usage = {k: v for k, v in body.get("usage", {}).items() if k in {"prompt_tokens", "completion_tokens", "total_tokens"} and type(v) is int and v >= 0}
                success = True
                self.last_success = datetime.now(timezone.utc).isoformat()
                self.last_error = None
                return Completion(text.strip(), usage)
            except httpx.TimeoutException:
                error = ProviderError("provider_timeout", True)
            except httpx.HTTPError:
                error = ProviderError("provider_network", True)
            except ProviderError as exc:
                error = exc
            except (ValueError, KeyError, IndexError, TypeError):
                error = ProviderError("provider_response_invalid")
            finally:
                self.admission.leave(success)
            self.last_error = error.code
            if attempt or not error.retryable or deadline - self.clock() <= retry_delay:
                raise error
            self.sleep(retry_delay)
        raise ProviderError("provider_unavailable")
