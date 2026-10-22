"""
BlackKnight - tool schemas + dispatcher.
"""

import json
import re

from sandbox import run_command, run_python, write_file, read_file
from skills import load_skill, skill_budget_left
from memory import remember, recall, forget


# ── flag validation ──
# Accepts: prefix{content} (any printable except whitespace/}) and 32-64 hex.
FLAG_RE = re.compile(
    r"^[A-Za-z0-9_]{2,32}\{[^}\s]{4,120}\}$"
    r"|^[a-fA-F0-9]{32,64}$"
)


def looks_like_flag(s: str) -> bool:
    s = (s or "").strip()
    if not s or " " in s or "\n" in s:
        return False
    return bool(FLAG_RE.match(s))


# ── schemas ──

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "write_plan",
            "description": (
                "MANDATORY before any environment action. Write the task plan "
                "to a markdown file. Split the work into role-based sub-agents, "
                "then list ordered concrete steps."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "objective": {
                        "type": "string",
                        "description": "One sentence: what success looks like.",
                    },
                    "sub_agents": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name":    {"type": "string"},
                                "role":    {"type": "string"},
                                "tools":   {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "output":  {"type": "string"},
                                "profile": {
                                    "type": "string",
                                    "description": (
                                        "Optional sub-agent profile name "
                                        "(see SUB-AGENT PROFILES in system "
                                        "prompt). Empty = inherit current."
                                    ),
                                },
                            },
                            "required": ["name", "role"],
                        },
                    },
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "success_criteria": {"type": "string"},
                },
                "required": ["objective", "sub_agents", "steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "act_as",
            "description": (
                "Declare which sub-agent from the plan you are acting as now. "
                "Call when switching roles. Switches to the sub-agent's "
                "declared profile automatically (different LLM/API if configured). "
                "Skip if you never switch."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sub_agent": {"type": "string"},
                    "focus":     {"type": "string"},
                    "profile": {
                        "type": "string",
                        "description": (
                            "Optional profile name to switch to. If omitted, "
                            "the plan's profile for this sub-agent is used; "
                            "if none, current stays."
                        ),
                    },
                },
                "required": ["sub_agent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Execute a shell command in the sandbox and return its output. "
                "Use only commands that exist on the current platform."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "default": 60},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute Python code in the sandbox and return stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "timeout": {"type": "integer", "default": 30},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write a file inside the sandbox directory. Use this to produce "
                "code, exploits, scripts, notes - WITHOUT executing them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the sandbox directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_flag",
            "description": (
                "Submit a REAL CTF flag captured from a target. "
                "Accepts ONLY a single flag string. "
                "Do NOT use this as a 'task done' signal - use finish()."
            ),
            "parameters": {
                "type": "object",
                "properties": {"flag": {"type": "string"}},
                "required": ["flag"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "think",
            "description": "Explicit planning step. Use when the next move is unclear.",
            "parameters": {
                "type": "object",
                "properties": {"reasoning": {"type": "string"}},
                "required": ["reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": (
                "Signal that the current task is complete WITHOUT a CTF flag "
                "(code written, explanation given, scan done, objective "
                "reached). Use this instead of submit_flag for non-flag tasks."
            ),
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": (
                "Pause and ask the operator a question when you are stuck, "
                "need a decision, or a required tool is missing and you cannot "
                "work around it. Use sparingly - only for real blockers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Concrete question for the operator.",
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional short context: what you tried, why it failed.",
                    },
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": (
                "DISABLED. The skill index is already in the system prompt. "
                "Do not call this; load only the skill matching the current "
                "task via load_skill."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": (
                "Load the full instructions of ONE skill by name. Load ONLY if "
                "the skill's description in the system-prompt index matches the "
                "CURRENT task. Max 2 loads per task."
            ),
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": (
                "Persist a fact across sessions. Use category='lesson' "
                "for self-report feedback after a task (key prefix 'win:' "
                "or 'fail:'). Examples: tool locations, host details, "
                "credentials found."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["general", "host", "lesson"],
                        "default": "general",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Search long-term memory. Empty query returns all.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "default": ""}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget",
            "description": "Remove a stale memory entry by key.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
        },
    },
]

# ── reflexion subset: memory tools only (no finish - enforced in main) ──

REFLEXION_SCHEMAS = [
    t for t in TOOL_SCHEMAS
    if t["function"]["name"] in ("remember", "recall", "forget", "think")
]


# ── dispatcher ──

def execute_tool(name: str, args: dict) -> str:
    """Dispatch tool call. ask_user and act_as are handled in main.py."""
    if not isinstance(args, dict):
        args = {}

    if name == "think":
        return json.dumps({"ok": True, "reasoning": args.get("reasoning", "")})

    if name == "write_plan":
        from planner import write_plan as _wp
        return json.dumps(_wp(
            objective=args.get("objective", ""),
            sub_agents=args.get("sub_agents") or [],
            steps=args.get("steps") or [],
            success_criteria=args.get("success_criteria", ""),
        ), ensure_ascii=False)

    if name == "act_as":
        sa = str(args.get("sub_agent", "")).strip() or "?"
        focus = str(args.get("focus", "")).strip()
        return json.dumps({
            "ok": True,
            "sub_agent": sa,
            "focus": focus,
            "reminder": (
                "You are now acting as sub-agent '" + sa + "'. "
                "Focus: " + (focus or "continue per plan") + ". "
                "Stay in this role until you call act_as again."
            ),
        }, ensure_ascii=False)

    if name == "finish":
        return json.dumps({
            "ok": True,
            "kind": "finish",
            "summary": args.get("summary", ""),
        })

    if name == "submit_flag":
        flag = (args.get("flag") or "").strip()
        if not looks_like_flag(flag):
            return json.dumps({
                "ok": False,
                "kind": "invalid",
                "error": "invalid_flag_format",
                "hint": (
                    "Not a real flag. If the task is done, call "
                    "finish(summary=...) instead. submit_flag is only for "
                    "actual flag strings read from the target."
                ),
                "received": flag,
            })
        return json.dumps({
            "ok": True,
            "kind": "flag",
            "flag": flag,
            "verified": False,
        })

    if name == "write_file":
        return json.dumps(
            write_file(args.get("path", ""), args.get("content", ""))
        )

    if name == "read_file":
        return json.dumps(read_file(args.get("path", "")))

    if name == "run_command":
        return json.dumps(run_command(
            args.get("command", ""),
            args.get("timeout", 60),
        ))

    if name == "run_python":
        return json.dumps(run_python(
            args.get("code", ""),
            args.get("timeout", 30),
        ))

    # ── skills ──
    if name == "list_skills":
        return json.dumps(
            {
                "ok": False,
                "error": "list_skills is disabled",
                "hint": (
                    "The skill index is already in the system prompt. "
                    "Pick the skill matching the current task and call "
                    "load_skill(name)."
                ),
            },
            ensure_ascii=False,
        )

    if name == "load_skill":
        if skill_budget_left() <= 0:
            return json.dumps(
                {
                    "ok": False,
                    "error": "skill_load_budget_exhausted",
                    "hint": (
                        "You already loaded the allowed number of skills "
                        "for this task. Work with what you have. If a "
                        "different skill is truly required, say so via "
                        "ask_user."
                    ),
                },
                ensure_ascii=False,
            )
        content = load_skill(args.get("name", ""))
        if content is None:
            return json.dumps({"ok": False, "error": "skill not found"})
        import skills as _skills
        _skills._loads_this_task += 1
        return json.dumps(
            {
                "ok": True,
                "name": args.get("name", ""),
                "content": content,
                "loads_left": skill_budget_left(),
            },
            ensure_ascii=False,
        )

    # ── memory ──
    if name == "remember":
        return json.dumps(
            remember(
                args.get("key", ""),
                args.get("value", ""),
                args.get("category", "general"),
            ),
            ensure_ascii=False,
        )

    if name == "recall":
        return json.dumps(recall(args.get("query", "")), ensure_ascii=False)

    if name == "forget":
        return json.dumps(forget(args.get("key", "")), ensure_ascii=False)

    return json.dumps({"error": "unknown tool: " + name})