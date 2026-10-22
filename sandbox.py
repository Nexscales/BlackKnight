"""
BlackKnight — sandbox execution layer.
"""

import os
import platform
import subprocess
from pathlib import Path

from config import (
    SANDBOX_DIR, MAX_OUTPUT, MAX_FILE_SIZE,
    DEFAULT_TIMEOUT, MAX_TIMEOUT,
    DANGEROUS_PATTERNS, DANGEROUS_REGEX,
)

IS_WINDOWS = platform.system() == "Windows"
PYTHON_BIN = "python" if IS_WINDOWS else "python3"


def truncate(s: str, n: int = MAX_OUTPUT) -> str:
    return s if len(s) <= n else s[:n] + "\n…[truncated]"


def is_dangerous(cmd: str) -> str | None:
    for p, rx in zip(DANGEROUS_PATTERNS, DANGEROUS_REGEX):
        if rx.search(cmd):
            return p
    return None


def decode(data: bytes) -> str:
    if not data:
        return ""
    for enc in ("utf-8", "cp866", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def safe_path(path: str) -> Path:
    """Resolve `path` inside SANDBOX_DIR; reject any escape (component-wise,
    not prefix-based — `sandbox_evil` must not be accepted for `sandbox`)."""
    if not path:
        raise ValueError("empty path")
    p = (SANDBOX_DIR / path).resolve()
    try:
        p.relative_to(SANDBOX_DIR)
    except ValueError:
        raise ValueError(f"path escapes sandbox: {path}")
    return p


# ── command execution ──

def run_command(cmd: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    timeout = min(int(timeout), MAX_TIMEOUT)
    if (bad := is_dangerous(cmd)):
        return {"error": "blocked by policy", "pattern": bad, "command": cmd}

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    # ── КРИТИЧНО: Popen вместо run, чтобы контролировать kill ──
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(SANDBOX_DIR),
            stdin=subprocess.DEVNULL,          # ← не ждать ввода
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
            ),
        )
    except Exception as e:
        return {"error": str(e), "command": cmd}

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return {
            "ok": proc.returncode == 0,
            "command": cmd,
            "stdout": truncate(decode(stdout)),
            "stderr": truncate(decode(stderr)),
            "returncode": proc.returncode,
            "platform": "windows" if IS_WINDOWS else "posix",
        }

    except subprocess.TimeoutExpired:
        # ── Kill entire process tree (Windows) ──
        if IS_WINDOWS:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=10,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        else:
            try:
                proc.kill()
            except Exception:
                pass

        # ── Close pipes so communicate() doesn't hang ──
        for p in (proc.stdout, proc.stderr):
            try:
                if p:
                    p.close()
            except Exception:
                pass

        return {
            "error": "timeout",
            "command": cmd,
            "timeout": timeout,
            "note": "process tree killed",
        }
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        return {"error": str(e), "command": cmd}
        
def run_python(code: str, timeout: int = 30) -> dict:
    timeout = min(int(timeout), MAX_TIMEOUT)
    tmp = SANDBOX_DIR / f".tmp_{os.urandom(4).hex()}.py"
    try:
        tmp.write_text(code, encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        r = subprocess.run(
            [PYTHON_BIN, str(tmp)], cwd=str(SANDBOX_DIR),
            capture_output=True, timeout=timeout, env=env,
        )
        return {
            "ok": True,
            "stdout": truncate(decode(r.stdout)),
            "stderr": truncate(decode(r.stderr)),
            "returncode": r.returncode,
        }
    except FileNotFoundError:
        return {
            "error": f"python interpreter '{PYTHON_BIN}' not found",
            "hint": "Install Python or set PYTHON_BIN.",
        }
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "timeout": timeout}
    except Exception as e:
        return {"error": str(e)}
    finally:
        tmp.unlink(missing_ok=True)


# ── file ops ──

def write_file(path: str, content: str) -> dict:
    try:
        p = safe_path(path)
        if len(content.encode("utf-8")) > MAX_FILE_SIZE:
            return {"error": "file too large"}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {
            "ok": True,
            "path": str(p.relative_to(SANDBOX_DIR)),
            "abs_path": str(p),
            "bytes": len(content.encode("utf-8")),
        }
    except Exception as e:
        return {"error": str(e)}


def read_file(path: str) -> dict:
    try:
        p = safe_path(path)
        if not p.exists():
            return {"error": "not found", "path": path}
        if not p.is_file():
            return {"error": "not a file", "path": path}
        size = p.stat().st_size
        limit = MAX_OUTPUT * 4 + 1000  # bytes → utf-8 chars, safe cap
        with p.open("rb") as f:
            raw = f.read(limit)
        data = raw.decode("utf-8", errors="replace")
        out = {"ok": True, "path": path, "content": truncate(data)}
        if size > limit:
            out["truncated"] = True
            out["size_bytes"] = size
        return out
    except Exception as e:
        return {"error": str(e)}
