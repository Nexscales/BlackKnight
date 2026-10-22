"""
BlackKnight - sub-agent profiles.

Auto-discovered from env:  BK_AGENT_<NAME>_(MODEL|BASE_URL|API_KEY|TIMEOUT)
Explicit in agents.json:   {"profiles": {"<name>": {}}}

Fields missing in a named profile inherit from "default".
Timeout defaults to 60s, connect_timeout to 10s (per profile override).
"""

import json
import os
from pathlib import Path

AGENTS_FILE = Path(__file__).parent / "agents.json"

_CTX = {"current": "default", "profiles": {}}
_INITED = False


def _discover_env_profiles() -> dict:
    found = {}
    prefix = "BK_AGENT_"
    suffixes = ("_BASE_URL", "_MODEL", "_API_KEY", "_TIMEOUT", "_CONNECT_TIMEOUT")
    for key in os.environ:
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix):]
        for suf in suffixes:
            if rest.endswith(suf):
                name_part = rest[: -len(suf)]
                if not name_part:
                    continue
                name = name_part.lower().replace("_", "-")
                found.setdefault(name, {})
                break
    return found


def _load_file() -> dict:
    if not AGENTS_FILE.exists():
        return {"profiles": {}, "default_profile": "default"}
    try:
        data = json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {"profiles": {}, "default_profile": "default"}
    data.setdefault("profiles", {})
    data.setdefault("default_profile", "default")
    return data


def _env_prefix(name: str) -> str:
    return "BK_AGENT_" + name.upper().replace("-", "_")


def _float_or(raw, env_key, fallback: float) -> float:
    v = raw if raw not in (None, "") else os.getenv(env_key, "")
    if v in (None, ""):
        return fallback
    try:
        return float(v)
    except (TypeError, ValueError):
        return fallback


def _resolve_one(name: str, raw: dict, default_resolved: dict) -> dict:
    pfx = _env_prefix(name)
    base_url = (raw.get("base_url") or os.getenv(pfx + "_BASE_URL") or "").strip()
    model    = (raw.get("model")    or os.getenv(pfx + "_MODEL")    or "").strip()
    api_key  = (raw.get("api_key")  or os.getenv(pfx + "_API_KEY")  or "").strip()

    if name != "default":
        base_url = base_url or default_resolved.get("base_url", "")
        model    = model    or default_resolved.get("model", "")
        api_key  = api_key  or default_resolved.get("api_key", "")

    timeout = _float_or(
        raw.get("timeout"),
        pfx + "_TIMEOUT",
        default_resolved.get("timeout", 60.0) if name != "default" else 60.0,
    )
    connect_timeout = _float_or(
        raw.get("connect_timeout"),
        pfx + "_CONNECT_TIMEOUT",
        default_resolved.get("connect_timeout", 10.0) if name != "default" else 10.0,
    )

    return {
        "name": name,
        "base_url": base_url,
        "model": model,
        "api_key": api_key,
        "timeout": timeout,
        "connect_timeout": connect_timeout,
    }


def init() -> None:
    global _INITED
    from config import BASE_URL, MODEL, API_KEY

    data = _load_file()

    default_resolved = _resolve_one(
        "default",
        data["profiles"].get("default", {}),
        {"base_url": BASE_URL, "model": MODEL, "api_key": API_KEY,
         "timeout": 60.0, "connect_timeout": 10.0},
    )
    default_resolved["base_url"] = default_resolved["base_url"] or BASE_URL
    default_resolved["model"]    = default_resolved["model"]    or MODEL
    default_resolved["api_key"]  = default_resolved["api_key"]  or API_KEY

    profiles = {"default": default_resolved}

    all_names = set(data["profiles"].keys()) | set(_discover_env_profiles().keys())
    all_names.discard("default")

    for name in all_names:
        raw = data["profiles"].get(name, {})
        resolved = _resolve_one(name, raw, default_resolved)
        if not resolved["api_key"]:
            continue
        profiles[name] = resolved

    _CTX["profiles"] = profiles

    prev = _CTX.get("current")
    if prev and prev in profiles:
        _CTX["current"] = prev
    else:
        wanted = data.get("default_profile", "default")
        _CTX["current"] = wanted if wanted in profiles else "default"
    _INITED = True


def get(name=None):
    if not _INITED:
        init()
    if name is None:
        name = _CTX.get("current") or "default"
    return _CTX["profiles"].get(name) or _CTX["profiles"].get("default", {})


def set_current(name):
    if not _INITED:
        init()
    if name in _CTX["profiles"]:
        _CTX["current"] = name
        return True
    return False


def reset_current():
    _CTX["current"] = "default"


def current_name():
    return _CTX.get("current") or "default"


def list_names():
    if not _INITED:
        init()
    return sorted(_CTX["profiles"].keys())


def exists(name):
    if not _INITED:
        init()
    return name in _CTX["profiles"]


def describe():
    if not _INITED:
        init()
    cur = current_name()
    lines = ["# SUB-AGENT PROFILES (active: " + cur + ")"]
    lines.append("Each sub-agent may declare a `profile` in write_plan.")
    lines.append("Available profiles (* = current):")
    for name in list_names():
        p = _CTX["profiles"][name]
        mark = "*" if name == cur else " "
        lines.append(
            " " + mark + " " + name + ": model=" + p["model"]
            + " @ " + p["base_url"]
            + " (timeout=" + str(int(p["timeout"])) + "s)"
        )
    return "\n".join(lines)