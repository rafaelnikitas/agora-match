"""Validated runtime configuration. Secrets never appear in repr or status payloads."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def integer(name: str, default: int, low: int, high: int) -> int:
    value = int(os.getenv(name, str(default)))
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


def flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name, str(default)).lower()
    if value not in {"true", "false", "1", "0"}:
        raise ValueError(f"{name} must be true or false")
    return value in {"true", "1"}


@dataclass(frozen=True)
class FoundrySettings:
    base_url: str = ""
    api_key: str = field(default="", repr=False)
    auth_mode: str = "auto"
    client_id: str = ""
    token_scope: str = "https://cognitiveservices.azure.com/.default"
    deployment: str = ""
    reader: str = ""
    writer: str = ""
    reviewer: str = ""
    reasoning_deployments: frozenset[str] = frozenset()
    reasoning_effort: str = ""
    timeout_seconds: int = 8
    budget_seconds: int = 24
    requests_per_minute: int = 24
    max_concurrency: int = 2
    circuit_failures: int = 3
    circuit_cooldown: int = 30

    @classmethod
    def from_env(cls) -> "FoundrySettings":
        return cls(
            base_url=os.getenv("AZURE_FOUNDRY_BASE_URL", "").rstrip("/"),
            api_key=os.getenv("AZURE_FOUNDRY_API_KEY", ""),
            auth_mode=os.getenv("AZURE_FOUNDRY_AUTH_MODE", "auto"),
            client_id=os.getenv("AZURE_CLIENT_ID", ""),
            token_scope=os.getenv("AZURE_FOUNDRY_TOKEN_SCOPE", cls.token_scope),
            deployment=os.getenv("AZURE_FOUNDRY_DEPLOYMENT", ""),
            reader=os.getenv("AZURE_FOUNDRY_READER_DEPLOYMENT", ""),
            writer=os.getenv("AZURE_FOUNDRY_WRITER_DEPLOYMENT", ""),
            reviewer=os.getenv("AZURE_FOUNDRY_REVIEWER_DEPLOYMENT", ""),
            reasoning_deployments=frozenset(x.strip() for x in os.getenv("AZURE_FOUNDRY_REASONING_DEPLOYMENTS", "").split(",") if x.strip()),
            reasoning_effort=os.getenv("AZURE_FOUNDRY_REASONING_EFFORT", ""),
            timeout_seconds=integer("AGORA_MODEL_TIMEOUT_SECONDS", 8, 1, 60),
            budget_seconds=integer("AGORA_ANSWER_BUDGET_SECONDS", 24, 3, 120),
            requests_per_minute=integer("AGORA_MODEL_CALLS_PER_MINUTE", 24, 1, 600),
            max_concurrency=integer("AGORA_MODEL_CONCURRENCY", 2, 1, 16),
            circuit_failures=integer("AGORA_CIRCUIT_FAILURES", 3, 1, 10),
            circuit_cooldown=integer("AGORA_CIRCUIT_COOLDOWN_SECONDS", 30, 1, 300),
        )

    @property
    def identity_mode(self) -> str:
        return ("api_key" if self.api_key else "managed_identity" if self.client_id else "unconfigured") if self.auth_mode == "auto" else self.auth_mode

    def errors(self) -> list[str]:
        errors = []
        if self.auth_mode not in {"auto", "api_key", "managed_identity", "default_credential"}:
            errors.append("unsupported_auth_mode")
        if self.reasoning_effort not in {"", "none", "low", "medium", "high"}:
            errors.append("unsupported_reasoning_effort")
        if self.base_url:
            suffixes = (".openai.azure.com", ".services.ai.azure.com", ".cognitiveservices.azure.com")
            try:
                u = urlsplit(self.base_url)
                project_path = (u.hostname or "").endswith(".services.ai.azure.com") and re.fullmatch(
                    r"/api/projects/[A-Za-z0-9][A-Za-z0-9_-]{0,63}/openai/v1", u.path)
                invalid = (u.scheme != "https" or not (u.hostname or "").endswith(suffixes) or u.port not in {None, 443}
                           or u.username or u.password or u.query or u.fragment
                           or (u.path != "/openai/v1" and not project_path))
            except ValueError:
                invalid = True
            if invalid:
                errors.append("invalid_azure_v1_endpoint")
        roles = [self.reader, self.writer, self.reviewer]
        if any(roles) and not all(roles):
            errors.append("incomplete_role_deployments")
        for name in [self.deployment, *roles]:
            if name and not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", name):
                errors.append("invalid_deployment_name")
                break
        if self.identity_mode == "api_key" and not self.api_key:
            errors.append("missing_api_key")
        if self.identity_mode == "managed_identity" and not self.client_id:
            errors.append("missing_managed_identity_client_id")
        return errors

    @property
    def configured(self) -> bool:
        return bool(self.base_url and (self.deployment or all((self.reader, self.writer, self.reviewer)))
                    and self.identity_mode in {"api_key", "managed_identity", "default_credential"} and not self.errors())

    @property
    def mode(self) -> str:
        return "three-role" if self.configured and self.reader else "single-model" if self.configured else "demo"


@dataclass(frozen=True)
class AppSettings:
    require_ai: bool = False
    api_requests_per_minute: int = 60
    cache_seconds: int = 60
    cache_entries: int = 128
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "testserver", "*.azurecontainerapps.io")

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            require_ai=flag("AGORA_REQUIRE_AI"),
            api_requests_per_minute=integer("AGORA_API_REQUESTS_PER_MINUTE", 60, 1, 1200),
            cache_seconds=integer("AGORA_CACHE_SECONDS", 60, 0, 3600),
            cache_entries=integer("AGORA_CACHE_ENTRIES", 128, 1, 1024),
            allowed_hosts=tuple(x.strip() for x in os.getenv("AGORA_ALLOWED_HOSTS", ",".join(cls.allowed_hosts)).split(",") if x.strip()),
        )
