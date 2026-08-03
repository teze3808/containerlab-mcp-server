from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, path: str, principal: str):
        self.path = Path(path).expanduser()
        self.principal = principal
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        os.close(fd)
        os.chmod(self.path, 0o600)

    def write(self, event: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "authenticated_principal": self.principal,
            **event,
        }
        line = json.dumps(record, separators=(",", ":"), default=str) + "\n"
        with self._lock:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.chmod(self.path, 0o600)
                os.write(fd, line.encode("utf-8"))
            finally:
                os.close(fd)
