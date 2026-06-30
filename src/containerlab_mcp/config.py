from __future__ import annotations

import os
from dataclasses import dataclass


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
    verify_tls: bool = False
    timeout: float = 30.0


def get_settings() -> Settings:
    api_url = os.getenv("CLAB_API_URL", "").rstrip("/")
    username = os.getenv("CLAB_USERNAME", "")
    password = os.getenv("CLAB_PASSWORD", "")
    timeout = float(os.getenv("CLAB_TIMEOUT", "30"))

    if not username:
        raise RuntimeError("CLAB_USERNAME is required")
    if not password:
        raise RuntimeError("CLAB_PASSWORD is required")
    if not api_url:
        raise RuntimeError("CLAB_API_URL is required")

    return Settings(
        api_url=api_url,
        username=username,
        password=password,
        verify_tls=_bool_env("CLAB_VERIFY_TLS", False),
        timeout=timeout,
    )
