"""
BlackKnight — session logger.
Каждый шаг агента пишется в JSONL. Консоль показывает только сводку.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from config import LOGS_DIR


class SessionLogger:
    _current: "SessionLogger | None" = None

    def __init__(self, model: str, mode: str):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = LOGS_DIR / f"session_{ts}.jsonl"
        self.model = model
        self.mode = mode
        self.start = time.time()
        self._fh = self.path.open("a", encoding="utf-8")
        self.log("session_start", model=model, mode=mode)

    def log(self, kind: str, **fields: Any) -> None:
        if self._fh.closed:
            return
        entry = {"t": round(time.time() - self.start, 3), "kind": kind, **fields}
        self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        """Idempotent — safe to call multiple times."""
        if self._fh.closed:
            return
        try:
            self.log("session_end", duration=round(time.time() - self.start, 2))
        finally:
            self._fh.close()

    @classmethod
    def current(cls) -> "SessionLogger | None":
        return cls._current

    @classmethod
    def set_current(cls, logger: "SessionLogger") -> None:
        cls._current = logger


def log_event(kind: str, **fields: Any) -> None:
    lg = SessionLogger.current()
    if lg:
        lg.log(kind, **fields)


def tail(path: Path, n: int = 20) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()[-n:]