"""
BlackKnight — persistent memory across sessions.
Stored as JSON. Injected into the system prompt at startup, and writable
via remember()/recall()/forget() tools.
"""

import json
import time
from pathlib import Path

MEM_DIR = Path(__file__).parent / "memory"
MEM_DIR.mkdir(exist_ok=True)
MEM_FILE = MEM_DIR / "memory.json"


def _load() -> dict:
    if MEM_FILE.exists():
        try:
            return json.loads(MEM_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"facts": {}, "hosts": {}}


def _save(data: dict) -> None:
    MEM_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _prune(
    max_lessons: int = 50,
    max_general: int = 200,
    max_hosts: int = 200,
    ttl_days: int = 30,
) -> None:
    """Drop entries older than ttl_days, and cap each bucket by count."""
    data = _load()
    now = time.time()
    ttl_sec = ttl_days * 24 * 3600

    def _fresh(entries: dict) -> dict:
        return {
            k: v for k, v in entries.items()
            if (now - v.get("ts", 0)) < ttl_sec
        }

    def _cap(entries: dict, limit: int) -> dict:
        if len(entries) <= limit:
            return entries
        newest = sorted(
            entries.items(),
            key=lambda kv: kv[1].get("ts", 0),
            reverse=True,
        )[:limit]
        return dict(newest)

    facts = _fresh(data.get("facts", {}))
    hosts = _fresh(data.get("hosts", {}))

    lessons = {k: v for k, v in facts.items() if v.get("category") == "lesson"}
    others  = {k: v for k, v in facts.items() if v.get("category") != "lesson"}

    lessons = _cap(lessons, max_lessons)
    others  = _cap(others, max_general)
    hosts   = _cap(hosts, max_hosts)

    data["facts"] = {**others, **lessons}
    data["hosts"] = hosts
    _save(data)


def remember(key: str, value: str, category: str = "general") -> dict:
    data = _load()
    entry = {"value": value, "ts": time.time()}
    if category == "host":
        data.setdefault("hosts", {})[key] = entry
    else:
        entry["category"] = category
        data.setdefault("facts", {})[key] = entry
    _save(data)
    _prune()
    return {"ok": True, "key": key, "category": category}


def recall(query: str = "") -> dict:
    data = _load()
    q = query.lower().strip()

    def match(k, v):
        if not q:
            return True
        return q in k.lower() or q in str(v.get("value", "")).lower()

    return {
        "ok": True,
        "facts": {k: v for k, v in data.get("facts", {}).items() if match(k, v)},
        "hosts": {k: v for k, v in data.get("hosts", {}).items() if match(k, v)},
    }


def forget(key: str) -> dict:
    data = _load()
    removed = False
    for bucket in ("facts", "hosts"):
        if key in data.get(bucket, {}):
            del data[bucket][key]
            removed = True
    _save(data)
    return {"ok": removed, "key": key}


def memory_summary(max_items: int = 25) -> str:
    data = _load()
    facts = list(data.get("facts", {}).items())[-max_items:]
    hosts = list(data.get("hosts", {}).items())[-max_items:]
    if not facts and not hosts:
        return ""
    lines = ["# MEMORY (from previous sessions)"]
    if facts:
        lines.append("## Facts")
        for k, v in facts:
            lines.append(f"- {k}: {v.get('value')}")
    if hosts:
        lines.append("## Known hosts")
        for k, v in hosts:
            lines.append(f"- {k}: {v.get('value')}")
    return "\n".join(lines)