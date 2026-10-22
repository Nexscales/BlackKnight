"""
BlackKnight — difficulty presets.

Each preset controls:
  - max_steps          hard step cap
  - temperature        LLM temperature (lower = fewer tokens, less wander)
  - max_tokens         completion cap (API-side)
  - trim_keep_recent   tool results kept intact before trimming
  - trim_old_chars     chars kept for each old tool result
  - plan_max_sub_agents  how many sub-agents the plan may declare
  - prompt_extra       text appended to the system prompt
"""

PRESETS = {
    "easy": {
        "label": "easy",
        "tagline": "40 steps · minimal tokens",
        "max_steps": 40,
        "temperature": 0.4,
        "max_tokens": 1024,
        "trim_keep_recent": 3,
        "trim_old_chars": 400,
        "plan_max_sub_agents": 2,
        "prompt_extra": """
# DIFFICULTY: EASY (token-saving mode)
- Be extremely terse. No preamble. No restating the task.
- ONE tool call per message. Do not narrate between steps.
- Do not summarise intermediate results — move straight to the next call.
- Max 2 <think> blocks for the whole task.
- Skip success confirmations. Only `finish(summary=...)` at the very end.
- If a step works — proceed immediately, never re-verify "just in case".
""",
    },
    "mid": {
        "label": "mid",
        "tagline": "80 steps · balanced",
        "max_steps": 80,
        "temperature": 0.5,
        "max_tokens": 2048,
        "trim_keep_recent": 5,
        "trim_old_chars": 800,
        "plan_max_sub_agents": 3,
        "prompt_extra": """
# DIFFICULTY: MID
- Balanced. Brief reasoning per step; no verbose explanations.
- One or two tool calls per message when tightly related.
""",
    },
    "hard": {
        "label": "hard",
        "tagline": "160 steps · thorough",
        "max_steps": 160,
        "temperature": 0.6,
        "max_tokens": 4096,
        "trim_keep_recent": 8,
        "trim_old_chars": 1500,
        "plan_max_sub_agents": 5,
        "prompt_extra": """
# DIFFICULTY: HARD
- Full reasoning per step allowed.
- Explore multiple vectors before committing to one.
- Consider fallbacks in <think> before each irreversible action.
""",
    },
    "hell": {
        "label": "hell",
        "tagline": "9999 steps · full power",
        "max_steps": 9999,
        "temperature": 0.7,
        "max_tokens": 8192,
        "trim_keep_recent": 12,
        "trim_old_chars": 3000,
        "plan_max_sub_agents": 10,
        "prompt_extra": """
# DIFFICULTY: HELL
- Maximum depth. Exhaustive enumeration of every plausible vector.
- Document failures in <think> and pivot methodically.
- No step-limit pressure — plan long-term.
- If one avenue is dead, name WHY in <think> and switch.
""",
    },
}

DIFFICULTY_ORDER = ["easy", "mid", "hard", "hell"]
DEFAULT_DIFFICULTY = "mid"
_CHOICE_MAP = {"1": "easy", "2": "mid", "3": "hard", "4": "hell"}


def get_preset(name: str) -> dict:
    return PRESETS.get(name) or PRESETS[DEFAULT_DIFFICULTY]


def is_valid(name: str | None) -> bool:
    return name in PRESETS


def from_choice(choice: str) -> str:
    return _CHOICE_MAP.get(choice.strip(), DEFAULT_DIFFICULTY)