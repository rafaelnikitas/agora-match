"""Safe operation events and optional Azure Monitor tracing; no prompts or credentials."""
from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Lock

_initialized = False
_lock = Lock()
logger = logging.getLogger("agora")
SAFE_FIELDS = {"request_id", "stage", "deployment", "duration_ms", "status", "reason", "mode", "cache_hit", "evidence_count", "http_status", "path", "trace_id", "prompt_tokens", "completion_tokens", "total_tokens"}


class OperationFormatter(logging.Formatter):
    def format(self, record):
        fields = {k: v for k, v in getattr(record, "operation", {}).items() if k in SAFE_FIELDS}
        return json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "event": record.getMessage(), **fields}, ensure_ascii=False)


def configure_observability():
    global _initialized
    with _lock:
        if _initialized:
            return
        handler = logging.StreamHandler()
        handler.setFormatter(OperationFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
            from azure.monitor.opentelemetry import configure_azure_monitor
            options = {}
            if os.getenv("AZURE_MONITOR_AUTH_MODE") == "managed_identity":
                from azure.identity import ManagedIdentityCredential
                client_id = os.environ["AZURE_CLIENT_ID"]
                options["credential"] = ManagedIdentityCredential(client_id=client_id)
            configure_azure_monitor(
                logger_name="agora", enable_live_metrics=False, disable_offline_storage=True,
                traces_per_second=2, **options,
            )
        # SDK logs must never emit HTTP headers or credential diagnostics in normal operation.
        logging.getLogger("azure").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        _initialized = True


def event(name: str, **fields):
    # Filter before creating the LogRecord, so Azure exporters receive the same
    # safe fields as the console formatter.
    logger.info(name, extra={"operation": {k: v for k, v in fields.items() if k in SAFE_FIELDS}})


@contextmanager
def span(name: str, **fields):
    from opentelemetry import trace
    with trace.get_tracer("agora.match").start_as_current_span(name) as current:
        for key, value in fields.items():
            if key in SAFE_FIELDS and isinstance(value, (str, bool, int, float)):
                current.set_attribute("agora." + key, value)
        yield current


def trace_id() -> str:
    from opentelemetry import trace
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else ""
