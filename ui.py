"""
BlackKnight - CLI rendering.
Console: concise. Full detail: ./logs/session_*.jsonl.
"""

import math
import threading
import time
from contextlib import contextmanager
from datetime import datetime

from rich.console import Console, Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.live import Live
from rich.rule import Rule
from rich.theme import Theme
from rich.box import ROUNDED, HEAVY

from config import MODEL, CONTEXT_WINDOW
from logger import log_event


PREVIEW_LINES       = 3
PREVIEW_LINE_LEN    = 110
FINAL_MAX_LINES     = 40
PLAN_PREVIEW_LINES  = 30


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
})

console = Console(theme=THEME)


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


# ── banner ──

def banner(mode: str, difficulty: str = "mid", max_steps: int = 80) -> Panel:
    art = Text()
    art.append(">>>  ", style="bk.brand")
    art.append("B L A C K", style="bold red")
    art.append("  K N I G H T", style="bold bright_red")
    art.append("  <<<", style="bk.brand")

    sub = Text("autonomous offensive security agent", style="bk.muted")

    meta = Text()
    meta.append("model  ", style="bk.muted"); meta.append(MODEL, style="bk.accent")
    meta.append("   ctx  ", style="bk.muted"); meta.append(_fmt_tokens(CONTEXT_WINDOW), style="bk.accent")
    meta.append("   steps  ", style="bk.muted"); meta.append(str(max_steps), style="bk.accent")
    meta.append("   mode  ", style="bk.muted"); meta.append(mode, style="bk.accent")
    meta.append("   diff  ", style="bk.muted"); meta.append(difficulty, style="bk.accent")
    meta.append("   profile  ", style="bk.muted"); meta.append(_profile_name(), style="bk.accent")

    hint = Text()
    hint.append("modes  ", style="bk.muted")
    hint.append(":auto", style="bright_red"); hint.append("  ", style="")
    hint.append(":chat", style="white"); hint.append("  ", style="")
    hint.append(":agent", style="bright_red")
    hint.append("     diff  ", style="bk.muted")
    hint.append(":diff easy|mid|hard|hell", style="bk.accent")
    hint.append("     profile  ", style="bk.muted")
    hint.append(":profiles", style="bk.accent"); hint.append("  ", style="")
    hint.append(":profile <name>", style="bk.accent")
    hint.append("     cmds  ", style="bk.muted")
    hint.append(":reset", style="bk.accent"); hint.append("  ", style="")
    hint.append(":log", style="bk.accent"); hint.append("  ", style="")
    hint.append(":last", style="bk.accent"); hint.append("  ", style="")
    hint.append(":tail", style="bk.accent"); hint.append("  ", style="")
    hint.append(":exit", style="bk.accent")

    ex = Text()
    ex.append("try  ", style="bk.muted")
    ex.append("\"привет\"", style="white")
    ex.append("   ", style="")
    ex.append("·", style="bk.dim")
    ex.append("   ", style="")
    ex.append("\"scan 10.10.10.5 with nmap\"", style="bright_red")

    return Panel(
        Group(art, sub, Text(""), meta, Text(""), hint, Text(""), ex),
        box=ROUNDED, border_style="bk.brand", padding=(1, 2),
    )


# ── reasoning bar ──

@contextmanager
def reasoning_bar(label: str = "reasoning"):
    stop = threading.Event()
    start = time.time()
    width = 44

    def render():
        while not stop.is_set():
            elapsed = time.time() - start
            pos = int((math.sin(elapsed * 4.0) + 1) / 2 * (width - 4))
            bar = Text()
            bar.append("─" * pos, style="bk.empt")
            bar.append("---", style="bk.pulse")
            bar.append("─" * (width - pos - 3), style="bk.empt")

            line = Text()
            line.append("  ▸ ", style="bk.accent")
            line.append(label + " ", style="bk.think")
            line.append_text(bar)
            line.append(f"  {elapsed:5.1f}s", style="bk.muted")

            live.update(line)
            time.sleep(0.05)

    with Live(console=console, refresh_per_second=24, transient=True) as live:
        t = threading.Thread(target=render, daemon=True)
        t.start()
        try:
            yield
        finally:
            stop.set()
            t.join(timeout=0.5)


# ── context bar ──

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
    bar.append("█" * filled, style=color)
    bar.append("░" * (width - filled), style="grey27")
    bar.append(f"  {pct*100:5.1f}%", style="grey62")
    bar.append(f"  {_fmt_tokens(used)}/{_fmt_tokens(total)}", style="grey37")
    return bar


def print_context_status(used: int, total: int):
    if not total:
        return
    console.print()
    console.print("  ", context_bar(used, total))


# ── concise printers ──

def print_thought(text: str):
    text = text.strip()
    if not text:
        return
    console.print()
    console.print(f"[bk.muted]\\[{ts()}][/] [bk.think]● thinking[/]")
    for line in text.splitlines()[:6]:
        if len(line) > PREVIEW_LINE_LEN:
            line = line[:PREVIEW_LINE_LEN] + "…"
        console.print(f"   [bk.think]{line}[/]")


def print_tool_call(name: str, args: dict):
    if name == "run_command":
        cmd = str(args.get("command", ""))
        if len(cmd) > PREVIEW_LINE_LEN:
            cmd = cmd[:PREVIEW_LINE_LEN] + "…"
        console.print()
        console.print(f"[bk.muted]\\[{ts()}][/] [bk.tool]▸ {name}[/]  [bk.dim]{cmd}[/]")
        return

    if name == "write_plan":
        obj = str(args.get("objective", ""))
        if len(obj) > PREVIEW_LINE_LEN:
            obj = obj[:PREVIEW_LINE_LEN] + "…"
        console.print()
        console.print(f"[bk.muted]\\[{ts()}][/] [bk.tool]▸ {name}[/]  [bk.dim]{obj}[/]")
        return

    if name == "act_as":
        sa = str(args.get("sub_agent", "?"))
        focus = str(args.get("focus", ""))
        if len(focus) > 80:
            focus = focus[:80] + "…"
        print_sub_agent(sa, focus)
        return

    if name in ("load_skill", "ask_user", "finish", "think", "remember", "recall"):
        preview = ""
        for k in ("name", "question", "summary", "key", "query"):
            if k in args:
                preview = str(args[k])
                break
        if len(preview) > PREVIEW_LINE_LEN:
            preview = preview[:PREVIEW_LINE_LEN] + "…"
        console.print()
        console.print(f"[bk.muted]\\[{ts()}][/] [bk.tool]▸ {name}[/]  [bk.dim]{preview}[/]")
        return

    console.print()
    console.print(f"[bk.muted]\\[{ts()}][/] [bk.tool]▸ {name}[/]")


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
    status, data = _tool_result_summary(name, result)
    console.print(
        f"[bk.muted]\\[{ts()}][/] [bk.result]✓[/] {name}  "
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
    console.print()
    console.print(f"[bk.muted]\\[{ts()}][/] [bk.accent]▸ blackknight[/]")
    console.print(Panel(
        Markdown(text),
        box=ROUNDED, border_style="bk.accent", padding=(0, 1),
    ))


def print_final(text: str):
    if not text.strip():
        return
    console.print()
    console.print(Rule(style="bk.dim"))
    body = text
    lines = body.splitlines()
    if len(lines) > FINAL_MAX_LINES:
        body = (
            "\n".join(lines[:FINAL_MAX_LINES])
            + f"\n\n… (+{len(lines)-FINAL_MAX_LINES} lines, see :log)"
        )
    console.print(Panel(
        Markdown(body),
        title="[bk.accent]final[/]",
        title_align="left",
        box=ROUNDED, border_style="bk.dim", padding=(0, 1),
    ))


def print_done(summary: str):
    if not summary.strip():
        return
    console.print()
    console.print(Panel(
        Markdown(summary),
        title="[bk.accent]done[/]",
        title_align="left",
        box=ROUNDED, border_style="bk.dim", padding=(0, 1),
    ))


def print_flag(flag: str):
    console.print()
    console.print(Panel(
        Text(f"FLAG CAPTURED: {flag}", style="bk.flag"),
        box=HEAVY, border_style="bk.accent", padding=(1, 2),
    ))


def print_error(text: str):
    console.print(f"[bk.error]\\[{ts()}] {text}[/]")


def print_step(i: int, max_steps: int = 80):
    console.print(f"[bk.dim]\\[{ts()}] step {i+1}/{max_steps}[/]")


def prompt_user_input() -> str:
    return console.input(f"\n[bk.user]\\[{ts()}] you[/] [bk.accent]▸[/] ").strip()


def prompt_ask_user(question: str, context: str = "") -> str:
    console.print()
    body = Text()
    if context:
        body.append("context: ", style="bk.muted")
        body.append(context + "\n\n", style="bk.dim")
    body.append(question, style="white")
    console.print(Panel(
        body,
        title="[bk.ask]agent asks[/]",
        title_align="left",
        box=ROUNDED, border_style="bk.ask", padding=(1, 2),
    ))
    return console.input(f"[bk.ask]\\[{ts()}] your answer[/] [bk.accent]▸[/] ").strip()


# ── commands for inspecting the log ──

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


# ── difficulty selection ──

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
            f"\n[bk.accent]select[/] [bk.muted](1-4, default=2)[/] ▸ "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return "mid"
    return from_choice(ans or "2")


# ── plan / sub-agent / profile printers ──

def print_plan(result: dict) -> None:
    md = result.get("markdown", "")
    path = result.get("path", "")
    n_sa = result.get("sub_agent_count", 0)
    n_st = result.get("step_count", 0)
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
    console.print()
    console.print(
        f"[bk.muted]\\[{ts()}][/] [bk.accent]◆ sub-agent: {name}[/]"
        + (f"  [bk.dim]{focus}[/]" if focus else "")
    )


def print_profile(name: str, model: str) -> None:
    console.print()
    console.print(
        f"[bk.muted]\\[{ts()}][/] [bk.accent]◆ profile: {name}[/]  "
        f"[bk.dim]{model}[/]"
    )