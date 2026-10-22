"""
BlackKnight — configuration and env.

Load order (later wins only if not already set):
    .env file  ->  os.environ  ->  defaults
"""

import os
import re
from pathlib import Path

# ── load .env ──
_ENV_FILE = Path(__file__).parent / ".env"

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
BASE_URL = os.getenv("BK_BASE_URL", "")
MODEL    = os.getenv("BK_MODEL", "")

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
SANDBOX_DIR = Path(os.getenv("BK_SANDBOX_DIR", "./sandbox")).resolve()
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

MAX_OUTPUT      = 30000
MAX_FILE_SIZE   = 5_000_000
DEFAULT_TIMEOUT = 60
MAX_TIMEOUT     = 120

LOGS_DIR = Path(os.getenv("BK_LOGS_DIR", "./logs")).resolve()
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