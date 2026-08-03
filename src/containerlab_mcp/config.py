from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_url: str
    username: str
    password: str
    verify_tls: bool = True
    timeout: float = 30.0
    safe_mode: bool = True
    allow_raw_commands: bool = False
    allow_shell_terminal: bool = False
    max_response_bytes: int = 1_000_000
    approval_ttl: int = 900
    audit_log: str = str(
        Path.home() / ".local/state/containerlab-mcp/audit.jsonl"
    )
    approval_db: str = str(
        Path.home() / ".local/state/containerlab-mcp/approvals.sqlite3"
    )


def get_settings() -> Settings:
    api_url = os.getenv("CLAB_API_URL", "").rstrip("/")
    username = os.getenv("CLAB_USERNAME", "")
    password = os.getenv("CLAB_PASSWORD", "")
    timeout = float(os.getenv("CLAB_TIMEOUT", "30"))
    max_response_bytes = int(os.getenv("CLAB_MAX_RESPONSE_BYTES", "1000000"))
    approval_ttl = int(os.getenv("CLAB_APPROVAL_TTL", "900"))

    if not username:
        raise RuntimeError("CLAB_USERNAME is required")
    if not password:
        raise RuntimeError("CLAB_PASSWORD is required")
    if not api_url:
        raise RuntimeError("CLAB_API_URL is required")
    if not api_url.startswith("https://"):
        raise RuntimeError("CLAB_API_URL must use HTTPS")
    if timeout <= 0:
        raise RuntimeError("CLAB_TIMEOUT must be greater than zero")
    if max_response_bytes < 1024:
        raise RuntimeError("CLAB_MAX_RESPONSE_BYTES must be at least 1024")
    if not 60 <= approval_ttl <= 86400:
        raise RuntimeError("CLAB_APPROVAL_TTL must be between 60 and 86400")

    return Settings(
        api_url=api_url,
        username=username,
        password=password,
        verify_tls=_bool_env("CLAB_VERIFY_TLS", True),
        timeout=timeout,
        safe_mode=_bool_env("CLAB_SAFE_MODE", True),
        allow_raw_commands=_bool_env("CLAB_ALLOW_RAW_COMMANDS", False),
        allow_shell_terminal=_bool_env("CLAB_ALLOW_SHELL_TERMINAL", False),
        max_response_bytes=max_response_bytes,
        approval_ttl=approval_ttl,
        audit_log=os.getenv(
            "CLAB_AUDIT_LOG",
            str(Path.home() / ".local/state/containerlab-mcp/audit.jsonl"),
        ),
        approval_db=os.getenv(
            "CLAB_APPROVAL_DB",
            str(Path.home() / ".local/state/containerlab-mcp/approvals.sqlite3"),
        ),
    )
