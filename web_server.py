"""
BlackKnight — Web Console server.
FastAPI + WebSocket обёртка над main.run_task().
Запуск: python web_server.py  (или run_web.bat)
ENV: BK_PORT (по умолчанию 8080), BK_HOST (по умолчанию 127.0.0.1)
"""
import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import MODEL, CONTEXT_WINDOW, BASE_URL
import ui
from main import run_task
import sys as _sys, os as _os
_os.environ["PYTHONUTF8"] = "1"
_os.environ["PYTHONIOENCODING"] = "utf-8"
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
        
HOST = os.environ.get("BK_HOST", "127.0.0.1")   # не светим агент в локалку
PORT = int(os.environ.get("BK_PORT", "8080"))    # батник передаёт BK_PORT
MODES = {"auto", "chat", "agent", "dev"}
DIFFS = {"easy", "mid", "hard", "hell"}


def detect_provider(model: str, base_url: str) -> str:
    s = (model + " " + base_url).lower()
    if "openrouter" in s: return "openrouter"
    if "deepseek" in s: return "deepseek"
    if "anthropic" in s or "claude" in s: return "anthropic"
    if "gemini" in s or "generativelanguage" in s: return "google"
    if "localhost" in s or "127.0.0.1" in s or "11434" in s: return "local"
    if "openai" in s or "gpt" in s: return "openai"
    return "unknown"


def human_window(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
    if n >= 1_000: return f"{n/1000:.0f}k"
    return str(n)


class ContextState:
    """Реальные токены из usage, между вызовами — эвристика chars//4."""
    def __init__(self, max_tokens: int):
        self.max = max_tokens
        self.chars = 0
        self.real_used = None
        self.messages = 0
        self.steps = 0
        self.tool_calls = 0

    def reset(self):
        self.chars = 0
        self.real_used = None
        self.messages = 0
        self.steps = 0
        self.tool_calls = 0

    def add(self, role, content):
        self.chars += len(content or "")
        self.messages += 1
        if role == "tool":
            self.tool_calls += 1
        return self.snapshot()

    def set_real(self, used, total):
        self.real_used = used
        if total:
            self.max = total
        return self.snapshot()

    def step(self):
        self.steps += 1
        return self.snapshot()

    def snapshot(self):
        used = self.real_used if self.real_used is not None else self.chars // 4
        max_tok = self.max or 128000
        percent = round(used / max_tok * 100, 2) if max_tok else 0
        level = ("ok" if percent < 50 else "warn" if percent < 75
                 else "hot" if percent < 90 else "critical")
        return {"used": used, "max": max_tok, "percent": percent,
                "level": level, "messages": self.messages,
                "steps": self.steps, "tool_calls": self.tool_calls}


STATE = ContextState(CONTEXT_WINDOW)


class Manager:
    def __init__(self):
        self.clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, msg: dict):
        dead = []
        data = json.dumps(msg, ensure_ascii=False)
        for ws in self.clients:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.disconnect(d)


manager = Manager()
_LOOP: asyncio.AbstractEventLoop | None = None
_RUN_ID = 0     # «слышимый» запуск: stop инкрементит → события старого рана глушатся
_ACTIVE = 0     # rid реально работающего потока (0 = свободно)


def emit(event: dict, rid: int | None = None):
    """Thread-safe emit — вызывается из воркеров ui.py."""
    if _LOOP is None or not _LOOP.is_running():
        return
    if rid is not None and rid != _RUN_ID:
        return
    asyncio.run_coroutine_threadsafe(manager.broadcast(event), _LOOP)


def _model_info() -> dict:
    return {"model": MODEL, "provider": detect_provider(MODEL, BASE_URL),
            "context_window": CONTEXT_WINDOW,
            "context_human": human_window(CONTEXT_WINDOW)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _LOOP
    _LOOP = asyncio.get_running_loop()
    yield


app = FastAPI(title="BlackKnight Web", lifespan=lifespan)
Path("static").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    # no-store: браузер не подсунет старую версию интерфейса
    return HTMLResponse(Path("static/index.html").read_text(encoding="utf-8"),
                        headers={"Cache-Control": "no-store"})


@app.get("/api/info")
async def api_info():
    return _model_info()


@app.get("/api/state")
async def api_state():
    return {"model": _model_info(), "context": STATE.snapshot(),
            "running": _ACTIVE != 0 and _ACTIVE == _RUN_ID}


def _ui_hooks(rid: int):
    """Мягко подключаемся к ui.py — если хука нет, сервер не падает."""
    for name, arg in (("set_web_mode", True), ("set_context_state", STATE)):
        fn = getattr(ui, name, None)
        if callable(fn):
            try: fn(arg)
            except Exception: pass
    fn = getattr(ui, "set_web_stream_callback", None)
    if callable(fn):
        try: fn(lambda e: emit(e, rid))
        except Exception: pass


async def run_agent_task(task: str, mode: str, difficulty: str, rid: int):
    global _ACTIVE
    STATE.reset()
    _ui_hooks(rid)
    await manager.broadcast({"type": "context", "data": STATE.snapshot()})
    await manager.broadcast({"type": "model_info", "data": _model_info()})
    await manager.broadcast({"type": "task_start",
                             "data": {"task": task, "mode": mode,
                                      "difficulty": difficulty}})
    try:
        result = await asyncio.to_thread(run_task, task, mode, difficulty)
        if rid == _RUN_ID:
            await manager.broadcast({"type": "task_result", "data": result})
    except Exception as e:
        if rid == _RUN_ID:
            await manager.broadcast({"type": "error", "data": str(e)})
    finally:
        if _ACTIVE == rid:
            _ACTIVE = 0
        if rid == _RUN_ID:
            await manager.broadcast({"type": "done", "data": True})


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    global _RUN_ID, _ACTIVE
    await manager.connect(ws)
    try:
        await ws.send_text(json.dumps({"type": "model_info", "data": _model_info()}))
        await ws.send_text(json.dumps({"type": "context", "data": STATE.snapshot()}))
        await ws.send_text(json.dumps({"type": "status", "data": {
            "running": _ACTIVE != 0 and _ACTIVE == _RUN_ID}}))
        while True:
            payload = json.loads(await ws.receive_text())
            t = payload.get("type")

            if t == "start_task":
                if _ACTIVE:
                    await ws.send_text(json.dumps({
                        "type": "error",
                        "data": "agent is busy — previous run still finishing in sandbox"}))
                    continue
                task = str(payload.get("task", "")).strip()
                if not task:
                    continue
                mode = payload.get("mode", "agent")
                mode = mode if mode in MODES else "agent"
                diff = payload.get("difficulty", "mid")
                diff = diff if diff in DIFFS else "mid"
                _RUN_ID += 1
                _ACTIVE = _RUN_ID
                asyncio.create_task(run_agent_task(task, mode, diff, _RUN_ID))

            elif t == "stop":
                # Мягкий abort: глушим события и освобождаем UI.
                # Поток в песочнице доработает сам (таймауты sandbox.py),
                # новый запуск не начнётся, пока он жив — без двух агентов сразу.
                if _ACTIVE:
                    _RUN_ID += 1
                    await manager.broadcast({"type": "log", "data": {
                        "level": "warn",
                        "text": "abort: UI detached — sandbox process finishes on its own"}})
                    await manager.broadcast({"type": "done", "data": True})

            elif t == "reset":
                STATE.reset()
                await manager.broadcast({"type": "context", "data": STATE.snapshot()})

    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


if __name__ == "__main__":
    print(f"[BlackKnight] web console → http://{HOST}:{PORT}   (Ctrl+C to stop)")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")