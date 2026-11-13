"""
BlackKnight - CLI rendering (opencode-style).
Console: concise. Full detail: ./logs/session_*.jsonl.
"""

import itertools
import threading
import time
from contextlib import contextmanager
from datetime import datetime

from rich.console import Console, Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.padding import Padding
from rich.text import Text
from rich.live import Live
from rich.rule import Rule
from rich.theme import Theme
from rich.box import ROUNDED, HEAVY

from config import MODEL, CONTEXT_WINDOW
from logger import log_event
import sys as _sys, os as _os
_os.environ["PYTHONUTF8"] = "1"
_os.environ["PYTHONIOENCODING"] = "utf-8"
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PREVIEW_LINES       = 3
PREVIEW_LINE_LEN    = 110
FINAL_MAX_LINES     = 40
PLAN_PREVIEW_LINES  = 30
VERSION             = "2.2.0"


THEME = Theme({
    "bk.brand":  "bold red",
    "bk.accent": "bright_red",
    "bk.muted":  "grey37",
    "bk.dim":    "grey27",
    "bk.think":  "italic red3",
    "bk.tool":   "bold bright_red",
    "bk.result": "white",
    "bk.error":  "bold red on grey11",
    "bk.flag":   "bold white on red",
    "bk.user":   "bold white",
    "bk.ask":    "bold yellow",
    "bk.pulse":  "bright_red",
    "bk.empt":   "grey19",
    "bk.ok":     "green",
    "bk.warn":   "yellow",
    "bk.dash":   "grey27",
})

console = Console(theme=THEME)

# ─── WebSocket bridge ────────────────────────────────────────────────────────

_web_stream_callback = None
_context_state = None
WEB_MODE = False

def set_web_stream_callback(cb):
    global _web_stream_callback
    _web_stream_callback = cb

def set_context_state(state):
    global _context_state
    _context_state = state

def set_web_mode(value: bool):
    global WEB_MODE
    WEB_MODE = value

def _emit(event):
    if _web_stream_callback:
        _web_stream_callback(event)

def _track(role, content):
    if _context_state is not None:
        snap = _context_state.add(role, str(content))
        _emit({"type": "context", "data": snap})

def emit_context(used: int, total: int):
    """Real token numbers from LLM usage. Called from main.py after each call."""
    if _context_state is not None:
        snap = _context_state.set_real(used, total)
        _emit({"type": "context", "data": snap})
    elif _web_stream_callback:
        # No state object — still emit a minimal snapshot
        percent = round(used / total * 100, 2) if total else 0
        _web_stream_callback({"type": "context", "data": {
            "used": used, "max": total, "percent": percent,
        }})

def _step():
    if _context_state is not None:
        snap = _context_state.step()
        _emit({"type": "context", "data": snap})

# ─── Helpers ─────────────────────────────────────────────────────────────────

def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _human_size(n: int) -> str:
    if n < 1024:
        return str(n) + " B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/1024/1024:.1f} MB"


def _fmt_tokens(n: int) -> str:
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n/1000:.1f}K"
    return f"{n/1_000_000:.2f}M"


def _profile_name() -> str:
    try:
        from agents import current_name as _cn
        return _cn()
    except Exception:
        return "default"


# ─── banner ──────────────────────────────────────────────────────────────────

def banner(mode: str, difficulty: str = "mid", max_steps: int = 80) -> Panel:
    head = Text()
    head.append(" ⬢ ", style="bk.brand")
    head.append("BlackKnight", style="bold white")
    head.append("  v" + VERSION, style="bk.dim")
    head.append("  ·  ", style="bk.dim")
    head.append("autonomous offensive security agent", style="bk.muted")

    meta = Text()
    meta.append("model ", style="bk.muted")
    meta.append(MODEL, style="bk.accent")
    meta.append("   ctx ", style="bk.muted")
    meta.append(_fmt_tokens(CONTEXT_WINDOW), style="bk.accent")
    meta.append("   steps ", style="bk.muted")
    meta.append(str(max_steps), style="bk.accent")
    meta.append("   mode ", style="bk.muted")
    meta.append(mode, style="bk.accent")
    meta.append("   diff ", style="bk.muted")
    meta.append(difficulty, style="bk.accent")
    meta.append("   profile ", style="bk.muted")
    meta.append(_profile_name(), style="bk.accent")

    hint = Text()
    hint.append(":auto :chat :agent :dev", style="bk.dim")
    hint.append("   :diff easy|mid|hard|hell", style="bk.dim")
    hint.append("   :profiles", style="bk.dim")
    hint.append("   :reset :log :last :tail", style="bk.dim")
    hint.append("   :exit", style="bk.dim")

    ex = Text()
    ex.append("try  ", style="bk.muted")
    ex.append("\"привет\"", style="white")
    ex.append("   ·   ", style="bk.dim")
    ex.append("\"scan 10.10.10.5 with nmap\"", style="bright_red")

    return Panel(
        Group(head, meta, Text(""), hint, ex),
        box=ROUNDED, border_style="bk.dash", padding=(0, 1),
    )


# ─── reasoning bar ───────────────────────────────────────────────────────────

_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_STEP_LABEL = ""


@contextmanager
def reasoning_bar(label: str = "thinking"):
    stop = threading.Event()
    start = time.time()
    frames = itertools.cycle(_SPINNER_FRAMES)

    def render():
        while not stop.is_set():
            elapsed = time.time() - start
            line = Text()
            line.append("  ", style="")
            line.append(next(frames), style="bk.accent")
            line.append(" " + label, style="bk.think")
            if _STEP_LABEL:
                line.append("  " + _STEP_LABEL, style="bk.dim")
            line.append(f"  {elapsed:4.1f}s", style="bk.dim")
            live.update(line)
            time.sleep(0.09)

    with Live(console=console, refresh_per_second=24, transient=True) as live:
        t = threading.Thread(target=render, daemon=True)
        t.start()
        try:
            yield
        finally:
            stop.set()
            t.join(timeout=0.5)


# ─── context bar (CLI) ───────────────────────────────────────────────────────

def context_bar(used: int, total: int, width: int = 20) -> Text:
    pct = min(used / total, 1.0) if total else 0.0
    filled = int(pct * width)

    if pct < 0.5:
        color = "green"
    elif pct < 0.8:
        color = "yellow"
    elif pct < 0.95:
        color = "bright_red"
    else:
        color = "red"

    bar = Text()
    bar.append("ctx ", style="bk.muted")
    bar.append("█" * filled, style=color)
    bar.append("░" * (width - filled), style="grey27")
    bar.append(f" {pct*100:4.1f}%", style="grey62")
    bar.append(f"  {_fmt_tokens(used)}/{_fmt_tokens(total)}", style="grey37")
    return bar


def print_context_status(used: int, total: int):
    if not total:
        return
    console.print()
    console.print("  ", context_bar(used, total))


# ─── concise printers ────────────────────────────────────────────────────────

def print_thought(text: str):
    text = text.strip()
    if not text:
        return
    console.print()
    console.print(f"[bk.dim]\\[{ts()}][/] [bk.think]● thinking[/]")
    for line in text.splitlines()[:6]:
        if len(line) > PREVIEW_LINE_LEN:
            line = line[:PREVIEW_LINE_LEN] + "…"
        console.print(f"   [bk.think]{line}[/]")
    _track("assistant", text)
    _emit({"type": "thought", "data": text})


def print_tool_call(name: str, args: dict):
    _track("assistant", f"{name} {args}")
    _emit({"type": "tool_call", "data": {"name": name, "args": args}})

    preview = ""
    for k in ("command", "objective", "sub_agent", "path", "code",
              "name", "question", "summary", "key", "query", "reasoning"):
        if k in args:
            preview = str(args[k])
            break
    if len(preview) > PREVIEW_LINE_LEN:
        preview = preview[:PREVIEW_LINE_LEN] + "…"

    console.print()
    line = f"[bk.muted]\\[{ts()}][/] [bk.accent]▸[/] [bold white]{name}[/]"
    if preview:
        line += f"  [bk.dim]{preview}[/]"
    console.print(line)

    if name == "act_as":
        sa = str(args.get("sub_agent", "?"))
        focus = str(args.get("focus", ""))
        if len(focus) > 80:
            focus = focus[:80] + "…"
        print_sub_agent(sa, focus)


def _tool_result_summary(name: str, result: str):
    import json as _json
    try:
        data = _json.loads(result)
    except Exception:
        data = None

    size = _human_size(len(result))

    if not isinstance(data, dict):
        return size, {}

    if data.get("error"):
        return (
            f"[bk.error]error[/]  {size}  "
            f"[bk.dim]{str(data.get('error'))[:60]}[/]",
            data,
        )

    if name == "run_command":
        rc = data.get("returncode", "?")
        out_len = len(data.get("stdout", "")) + len(data.get("stderr", ""))
        return f"[bk.ok]rc={rc}[/]  {_human_size(out_len)}", data

    if name == "run_python":
        rc = data.get("returncode", "?")
        out_len = len(data.get("stdout", "")) + len(data.get("stderr", ""))
        return f"[bk.ok]rc={rc}[/]  {_human_size(out_len)}", data

    if name == "write_file":
        return f"[bk.ok]wrote {data.get('path')}[/]  {_human_size(data.get('bytes', 0))}", data

    if name == "read_file":
        content = data.get("content")
        if isinstance(content, str):
            return f"[bk.ok]read {data.get('path')}[/]  {_human_size(len(content))}", data
        return f"[bk.ok]read {data.get('path')}[/]  {size}", data

    if name == "load_skill":
        n = len(data.get("content", ""))
        return f"[bk.ok]skill '{data.get('name')}'[/]  {_human_size(n)}", data

    if name == "remember":
        return f"[bk.ok]remembered[/]  {data.get('key')}", data

    if name == "recall":
        f = len(data.get("facts", {}))
        h = len(data.get("hosts", {}))
        return f"[bk.ok]{f} facts, {h} hosts[/]", data

    if name == "write_plan":
        if data.get("ok"):
            return (
                f"[bk.ok]plan written[/]  "
                f"{data.get('sub_agent_count', 0)} sub-agents, "
                f"{data.get('step_count', 0)} steps",
                data,
            )
        return f"[bk.error]plan rejected[/]  {data.get('error', '')}", data

    if name == "act_as":
        return f"[bk.ok]role →[/] [bk.accent]{data.get('sub_agent', '?')}[/]", data

    if name == "finish":
        s = str(data.get("summary", ""))[:80]
        return f"[bk.accent]finish[/]  [bk.dim]{s}[/]", data

    if name == "submit_flag":
        return f"[bk.ok]flag[/]  {data.get('flag')}", data

    if name == "think":
        return "[bk.ok]logged[/]", data

    if name == "ask_user":
        return "[bk.ok]answered[/]", data

    return f"[bk.ok]ok[/]  {size}", data


def print_tool_result(name: str, result: str, elapsed: float):
    _track("tool", result)
    _emit({"type": "tool_result", "data": {
        "name": name, "elapsed": round(elapsed, 2),
        "result": (result or "")[:4000],
    }})

    status, data = _tool_result_summary(name, result)
    failed = isinstance(data, dict) and (data.get("error") or data.get("ok") is False)
    mark = "[bk.error]✗[/]" if failed else "[bk.ok]✓[/]"
    console.print(
        f"[bk.muted]\\[{ts()}][/] {mark} [bold]{name}[/] "
        f"[bk.dim]({elapsed:.2f}s)[/]  {status}"
    )

    if name == "write_plan" and isinstance(data, dict) and data.get("ok"):
        print_plan(data)
        log_event(
            "tool_result",
            name=name, elapsed=round(elapsed, 3),
            size=len(result), result=result,
        )
        return

    if isinstance(data, dict):
        out = (data.get("stdout") or data.get("stderr") or "").strip()
        if out:
            lines = [ln for ln in out.splitlines() if ln.strip()][:PREVIEW_LINES]
            total = len(out.splitlines())
            for ln in lines:
                if len(ln) > PREVIEW_LINE_LEN:
                    ln = ln[:PREVIEW_LINE_LEN] + "…"
                console.print(f"   [bk.dim]│[/] {ln}")
            if total > PREVIEW_LINES:
                console.print(
                    f"   [bk.dim]│ … +{total - PREVIEW_LINES} more lines "
                    f"(full: :last or :log)[/]"
                )

    log_event(
        "tool_result",
        name=name, elapsed=round(elapsed, 3),
        size=len(result), result=result,
    )


def print_chat(text: str):
    if not text.strip():
        return
    _track("assistant", text)
    _emit({"type": "chat", "data": text})
    console.print()
    console.print(f"[bk.muted]\\[{ts()}][/] [bold white]●[/] [bk.accent]blackknight[/]")
    console.print(Padding(Markdown(text), (0, 2)))


def print_final(text: str):
    if not text.strip():
        return
    _track("assistant", text)
    _emit({"type": "final", "data": text})
    console.print()
    console.print(Rule(style="bk.dash"))
    body = text
    lines = body.splitlines()
    if len(lines) > FINAL_MAX_LINES:
        body = (
            "\n".join(lines[:FINAL_MAX_LINES])
            + f"\n\n… (+{len(lines)-FINAL_MAX_LINES} lines, see :log)"
        )
    console.print(f"[bold white]●[/] [bk.accent]blackknight[/]")
    console.print(Padding(Markdown(body), (0, 2)))


def print_done(summary: str):
    if not summary.strip():
        return
    _track("assistant", summary)
    _emit({"type": "done", "data": summary})
    console.print()
    console.print(f"[bk.muted]\\[{ts()}][/] [bk.ok]▪ done[/]")
    console.print(Padding(Markdown(summary), (0, 2)))


def print_flag(flag: str):
    _emit({"type": "flag", "data": flag})
    console.print()
    console.print(Panel(
        Text("🚩  FLAG CAPTURED: " + flag, style="bk.flag"),
        box=HEAVY, border_style="bk.accent", padding=(1, 2),
    ))


def print_error(text: str):
    _emit({"type": "error", "data": text})
    console.print(f"[bk.error]\\[{ts()}] ✗ {text}[/]")


def print_step(i: int, max_steps: int = 80):
    global _STEP_LABEL
    _STEP_LABEL = f"step {i+1}/{max_steps}"
    _step()
    _emit({"type": "step", "data": {"i": i + 1, "max": max_steps}})


def prompt_user_input() -> str:
    if WEB_MODE:
        return ""
    console.print()
    return console.input(f"[bk.accent]▸[/] ").strip()


def prompt_ask_user(question: str, context: str = "") -> str:
    # Web mode: auto-answer instead of blocking on stdin
    if WEB_MODE:
        _emit({"type": "ask_user", "data": {"question": question, "context": context}})
        console.print(f"[bk.ask]\\[{ts()}] ask_user (web): {question}[/]")
        console.print("[bk.muted]  → auto-proceed with best judgment[/]")
        return "(web mode: proceeding with best judgment — no interactive user)"

    console.print()
    body = Text()
    if context:
        body.append("context: ", style="bk.muted")
        body.append(context + "\n\n", style="bk.dim")
    body.append(question, style="white")
    console.print(Padding(body, (0, 0)))
    return console.input(
        f"[bk.ask]? your answer[/] [bk.accent]▸[/] "
    ).strip()


# ─── commands for inspecting the log ────────────────────────────────────────

def print_log_path(path):
    console.print(f"[bk.muted]current log:[/] [bk.accent]{path}[/]")


def print_log_tail(path, n: int = 20):
    from logger import tail
    lines = tail(path, n)
    if not lines:
        console.print("[bk.muted]log is empty.[/]")
        return
    console.print(f"[bk.muted]last {len(lines)} entries in {path.name}:[/]")
    import json
    for raw in lines:
        try:
            e = json.loads(raw)
        except Exception:
            console.print(f"  [bk.dim]{raw[:120]}[/]")
            continue
        t = e.get("t", 0)
        kind = e.get("kind", "?")
        if kind == "tool_result":
            name = e.get("name", "?")
            size = e.get("size", 0)
            console.print(
                f"  [bk.dim]{t:7.2f}s[/]  {kind:14}  "
                f"[bk.tool]{name}[/]  {size} B"
            )
        else:
            console.print(f"  [bk.dim]{t:7.2f}s[/]  {kind}")


def print_last_tool_result(path):
    import json
    if not path.exists():
        console.print("[bk.muted]no log yet.[/]")
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    for raw in reversed(lines):
        try:
            e = json.loads(raw)
        except Exception:
            continue
        if e.get("kind") == "tool_result":
            name = e.get("name", "?")
            console.print()
            console.print(Rule(style="bk.dim"))
            console.print(f"[bk.accent]last tool result:[/] [bk.tool]{name}[/]")
            console.print(Rule(style="bk.dim"))
            console.print(e.get("result", ""))
            return
    console.print("[bk.muted]no tool results yet.[/]")


# ─── difficulty selection ───────────────────────────────────────────────────

def print_difficulty_menu() -> None:
    console.print()
    console.print("[bk.accent]select difficulty:[/]")
    console.print("  [bold bright_red]1[/]  [bold]easy[/]   [bk.muted]40 steps · minimal tokens[/]")
    console.print("  [bold bright_red]2[/]  [bold]mid[/]    [bk.muted]80 steps · balanced[/]")
    console.print("  [bold bright_red]3[/]  [bold]hard[/]   [bk.muted]160 steps · thorough[/]")
    console.print("  [bold bright_red]4[/]  [bold]hell[/]   [bk.muted]9999 steps · full power[/]")


def prompt_difficulty() -> str:
    from difficulty import from_choice
    print_difficulty_menu()
    try:
        ans = console.input(
            f"[bk.accent]select[/] [bk.muted](1-4, default=2)[/] [bk.accent]▸[/] "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return "mid"
    return from_choice(ans or "2")


# ─── plan / sub-agent / profile printers ────────────────────────────────────

def print_plan(result: dict) -> None:
    md = result.get("markdown", "")
    path = result.get("path", "")
    n_sa = result.get("sub_agent_count", 0)
    n_st = result.get("step_count", 0)
    _emit({"type": "plan", "data": {
        "markdown": md[:3000],
        "path": path,
        "title": result.get("objective") or "",
        "sub_agents": result.get("sub_agents") or [],
        "steps": result.get("steps") or [],
        "sub_agents_count": n_sa,
        "steps_count": n_st,
    }})
    console.print()
    console.print(
        f"[bk.muted]\\[{ts()}][/] [bk.accent]◆ plan written[/]  "
        f"[bk.dim]{path}  ({n_sa} sub-agents, {n_st} steps)[/]"
    )
    lines = md.splitlines()
    for ln in lines[:PLAN_PREVIEW_LINES]:
        console.print(f"   [bk.dim]│[/] {ln}")
    if len(lines) > PLAN_PREVIEW_LINES:
        console.print(
            f"   [bk.dim]│ … +{len(lines) - PLAN_PREVIEW_LINES} more lines "
            f"(file: {path})[/]"
        )


def print_sub_agent(name: str, focus: str) -> None:
    _emit({"type": "sub_agent", "data": {"name": name, "focus": focus}})
    console.print(
        f"   [bk.muted]↳ role[/] [bk.accent]{name}[/]"
        + (f"  [bk.dim]{focus}[/]" if focus else "")
    )


def print_profile(name: str, model: str) -> None:
    _emit({"type": "profile", "data": {"name": name, "model": model}})
    console.print(
        f"   [bk.muted]↳ profile[/] [bk.accent]{name}[/]  [bk.dim]{model}[/]"
    )


# ─── opencode-style footer / status line ────────────────────────────────────

def status_line(mode: str, difficulty: str, max_steps: int,
                profile: str, used: int, total: int) -> Text:
    line = Text()
    line.append(" ", style="")
    line.append(mode.upper(), style="bold white on red" if mode == "agent" else "bold white")
    line.append("  ", style="")
    line.append(f"diff:{difficulty}", style="bk.muted")
    line.append("  ", style="")
    line.append(f"steps:{max_steps}", style="bk.muted")
    line.append("  ", style="")
    line.append(f"profile:{profile}", style="bk.muted")
    line.append("  ", style="")
    pct = (used / total * 100) if total else 0
    color = "green" if pct < 50 else "yellow" if pct < 80 else "bright_red"
    line.append(f"ctx {pct:.0f}%", style=color)
    line.append("  ", style="")
    line.append(":help", style="bk.dim")
    return line


def print_status_bar(mode: str, difficulty: str, max_steps: int,
                     profile: str, used: int, total: int):
    console.print(Rule(style="bk.dash"))
    console.print(status_line(mode, difficulty, max_steps, profile, used, total))


HELP_TEXT = """
[bk.accent]commands[/]
  [bold]:auto[/] [bk.dim]:chat[/] [bold]:agent[/] [bold]:dev[/]      switch mode
  [bold]:diff[/] easy|mid|hard|hell    difficulty preset
  [bold]:profiles[/]                   list sub-agent LLM profiles
  [bold]:profile[/] <name>             switch profile manually
  [bold]:reset[/]                      clear context, plan, profile
  [bold]:log[/] [bk.dim]:tail[/] [bk.dim]:last[/]              inspect session log
  [bold]:clear[/]                      clear the screen
  [bold]:help[/]                       this message
  [bold]:exit[/] [bk.dim]:q[/]                  quit
"""


def print_help():
    console.print(HELP_TEXT)