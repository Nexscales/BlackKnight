"""
BlackKnight - task plan writer.

Flow:
  1. set_context(task, difficulty, max_steps)  - called by run_turn()
  2. reset_plan()                              - clears plan-written flag
  3. agent calls write_plan(...)               - tool dispatcher calls write_plan()
  4. mark_plan_written(path)                   - enables real tools
"""

import re
from datetime import datetime
from pathlib import Path

PLANS_DIR = Path(__file__).parent / "plans"
PLANS_DIR.mkdir(exist_ok=True)

_SLUG_RE = re.compile(r"[^a-z0-9]+")

_CTX = {
    "task": "",
    "difficulty": "mid",
    "max_steps": 80,
    "plan_written": False,
    "plan_path": "",
    "sub_agents": [],
}


def set_context(task: str, difficulty: str, max_steps: int) -> None:
    _CTX["task"] = task or ""
    _CTX["difficulty"] = difficulty
    _CTX["max_steps"] = max_steps


def get_context() -> dict:
    return dict(_CTX)


def reset_plan() -> None:
    _CTX["plan_written"] = False
    _CTX["plan_path"] = ""
    _CTX["sub_agents"] = []


def is_plan_written() -> bool:
    return bool(_CTX.get("plan_written"))


def mark_plan_written(path: str) -> None:
    _CTX["plan_written"] = True
    _CTX["plan_path"] = path


def get_sub_agent_profile(name: str) -> str:
    """Return the profile name declared for this sub-agent, or ''."""
    for sa in _CTX.get("sub_agents", []):
        if str(sa.get("name", "")) == name:
            return str(sa.get("profile", "") or "")
    return ""


def _slug(text: str, max_len: int = 40) -> str:
    s = _SLUG_RE.sub("-", (text or "").lower()).strip("-")
    return s[:max_len] or "task"


def _build_markdown(
    task: str,
    objective: str,
    sub_agents: list,
    steps: list,
    success_criteria: str,
    difficulty: str,
    max_steps: int,
) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Plan - " + (objective or task or "task"),
        "",
        "- **Created:** " + ts,
        "- **Task:** " + (task or "(none)"),
        "- **Difficulty:** `" + difficulty + "` (max " + str(max_steps) + " steps)",
        "",
        "## Objective",
        "",
        (objective or task or "_Not specified._").strip(),
        "",
        "## Sub-agents",
        "",
    ]

    if not sub_agents:
        lines.append("_No sub-agents - single-agent task._")
    else:
        for i, sa in enumerate(sub_agents, 1):
            if not isinstance(sa, dict):
                sa = {"name": "agent-" + str(i)}
            name = str(sa.get("name", "agent-" + str(i))).strip()
            role = str(sa.get("role", "")).strip()
            tools = sa.get("tools") or []
            if isinstance(tools, str):
                tools = [tools]
            output = str(sa.get("output", "")).strip()
            profile = str(sa.get("profile", "")).strip()
            lines.append("### `" + name + "`")
            if role:
                lines.append("- **Role:** " + role)
            if tools:
                lines.append("- **Tools:** " + ", ".join(str(t) for t in tools))
            if output:
                lines.append("- **Deliverable:** " + output)
            if profile:
                lines.append("- **Profile:** `" + profile + "`")
            lines.append("")

    lines += ["## Steps", ""]
    if steps:
        for i, step in enumerate(steps, 1):
            lines.append(str(i) + ". " + str(step))
    else:
        lines.append("_No steps listed._")

    lines += [
        "",
        "## Success criteria",
        "",
        (success_criteria or "_Not specified._").strip(),
        "",
    ]
    return "\n".join(lines)


def write_plan(
    objective: str,
    sub_agents: list,
    steps: list,
    success_criteria: str,
) -> dict:
    ctx = get_context()
    difficulty = ctx["difficulty"]
    max_steps = ctx["max_steps"]
    task = ctx["task"]

    from difficulty import get_preset
    from agents import exists as profile_exists, list_names as profile_names

    max_sa = get_preset(difficulty).get("plan_max_sub_agents", 5)
    if len(sub_agents) > max_sa:
        return {
            "ok": False,
            "error": "too_many_sub_agents",
            "limit": max_sa,
            "difficulty": difficulty,
            "hint": "Difficulty '" + difficulty + "' allows at most "
                    + str(max_sa) + " sub-agents. Consolidate roles and retry.",
        }

    # validate profile names against the resolved set
    for sa in sub_agents:
        if not isinstance(sa, dict):
            continue
        prof = str(sa.get("profile", "") or "")
        if prof and not profile_exists(prof):
            return {
                "ok": False,
                "error": "unknown_profile: " + prof,
                "available_profiles": profile_names(),
                "hint": "Pick a profile name that exists in agents.json / env.",
            }

    _CTX["sub_agents"] = list(sub_agents)

    md = _build_markdown(
        task=task,
        objective=objective,
        sub_agents=sub_agents,
        steps=steps,
        success_criteria=success_criteria,
        difficulty=difficulty,
        max_steps=max_steps,
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = PLANS_DIR / ("plan_" + ts + "_" + _slug(task or objective) + ".md")
    path.write_text(md, encoding="utf-8")
    mark_plan_written(str(path))

    return {
        "ok": True,
        "path": str(path),
        "abs_path": str(path.resolve()),
        "sub_agent_count": len(sub_agents),
        "step_count": len(steps),
        "markdown": md,
    }