"""
BlackKnight — skill library.
Skills live as markdown files in ./skills with frontmatter metadata.

LAZY LOADING MODEL:
- The system prompt embeds a compact INDEX (name + description only).
- The model loads ONLY the skill that matches the current task.
- A per-task budget caps how many skills can be loaded, so a 9B model
  cannot dump the whole library into context.
"""

import re
from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills"
SKILLS_DIR.mkdir(exist_ok=True)

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

# ── load budget ──
MAX_LOADS_PER_TASK = 2          # hard cap enforced by dispatcher
_loads_this_task = 0


def reset_skill_budget() -> None:
    """Called at the start of every new operator task."""
    global _loads_this_task
    _loads_this_task = 0


def skill_budget_left() -> int:
    return max(0, MAX_LOADS_PER_TASK - _loads_this_task)


def _parse_meta(block: str) -> dict:
    meta = {}
    for line in block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def list_skills() -> list[dict]:
    out = []
    for f in sorted(SKILLS_DIR.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        m = _FM.match(text)
        if m:
            meta = _parse_meta(m.group(1))
            out.append({
                "name": meta.get("name", f.stem),
                "description": meta.get("description", ""),
            })
        else:
            out.append({"name": f.stem, "description": ""})
    return out


def skills_index() -> str:
    """Compact index for the system prompt. Descriptions only, no bodies."""
    skills = list_skills()
    if not skills:
        return ""
    lines = [
        "# SKILL INDEX (names + one-line descriptions ONLY)",
        "Full skill bodies are NOT loaded. Load one only when its",
        "description matches the CURRENT task:",
        "",
    ]
    for s in skills:
        d = s.get("description") or "no description"
        lines.append(f"- {s['name']}: {d}")
    lines.append("")
    lines.append(f"Budget: at most {MAX_LOADS_PER_TASK} load_skill calls per task.")
    return "\n".join(lines)


def load_skill(name: str) -> str | None:
    """Load a skill body by name. Budget is checked by the dispatcher."""
    for f in SKILLS_DIR.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        m = _FM.match(text)
        if m:
            meta = _parse_meta(m.group(1))
            if meta.get("name") == name or f.stem == name:
                return m.group(2).strip()
        elif f.stem == name:
            return text.strip()
    return None
