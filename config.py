"""
BlackKnight — configuration and env.

Load order (later wins only if not already set):
    .env file  ->  os.environ  ->  defaults
"""

import os
import re
from pathlib import Path
import sys as _sys, os as _os
_os.environ["PYTHONUTF8"] = "1"
_os.environ["PYTHONIOENCODING"] = "utf-8"
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── project root ──
# All relative paths are resolved against the project folder, NOT the
# current working directory, so the app behaves the same when started
# from a shortcut, another folder, or a different drive.
BASE_DIR = Path(__file__).resolve().parent

# ── load .env ──
_ENV_FILE = BASE_DIR / ".env"

def _load_dotenv() -> None:
    if not _ENV_FILE.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_FILE, override=False)
        return
    except ImportError:
        pass
    for raw in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val

_load_dotenv()

# ── LLM provider ──
# Defaults match README.md; .env values win when set.
BASE_URL = os.getenv("BK_BASE_URL", "https://anymodel.org/v1").strip()
MODEL    = os.getenv("BK_MODEL", "cx/gpt-6-luna").strip()

API_KEY = os.getenv("BK_API_KEY", "").strip()
if not API_KEY:
    raise SystemExit(
        "BK_API_KEY is not set.\n"
        "  Put it in .env (recommended):    BK_API_KEY=sk-...\n"
        "  Or set it in the shell:\n"
        "    Windows cmd:   set BK_API_KEY=sk-...\n"
        "    PowerShell:    $env:BK_API_KEY='sk-...'\n"
        "    bash/zsh:      export BK_API_KEY=sk-...\n"
    )

# ── agent ──
# BK_MAX_STEPS is now a fallback for the difficulty preset; prefer -d/--difficulty.
MAX_STEPS = int(os.getenv("BK_MAX_STEPS", "80"))
CONTEXT_WINDOW = int(os.getenv("BK_CONTEXT_WINDOW", "1000000"))

# env override for interactive difficulty selection; CLI -d wins over this.
DIFFICULTY_ENV = os.getenv("BK_DIFFICULTY", "").lower().strip()

# ── sandbox ──
def _resolve_dir(value: str, fallback: str) -> Path:
    raw = (value or fallback).strip() or fallback
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = BASE_DIR / p
    return p.resolve()


SANDBOX_DIR = _resolve_dir(os.getenv("BK_SANDBOX_DIR", "./sandbox"), "./sandbox")
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

MAX_OUTPUT      = 40000
MAX_FILE_SIZE   = 20_000_000
DEFAULT_TIMEOUT = 1800
MAX_TIMEOUT     = 2600

LOGS_DIR = _resolve_dir(os.getenv("BK_LOGS_DIR", "./logs"), "./logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf?\s+/\s*(?:$|[&;|*])",
    r"\brm\s+-rf?\s+/\*",
    r"\bmkfs(?:\.\w+)?\b",
    r"\bformat\s+c:\s*(?:$|[&;|/\\])",
    r"\bdel\s+/f\s+/s\s+/q\s+c:\\",
    r"\bshutdown\s+/[sr]\b",
]
DANGEROUS_REGEX = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]