#!/usr/bin/env python3
"""
BlackKnight — frameless desktop shell.
Поднимает web_server.app в фоне и открывает его в безрамочном окне pywebview.
Windows: EdgeChromium / WebView2.  Запуск: python desktop.py  или  run_desktop.bat
"""
import ctypes
import json
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path

os.environ["BK_HOST"] = "127.0.0.1"

import uvicorn
import webview
from web_server import app, PORT
import sys as _sys, os as _os
_os.environ["PYTHONUTF8"] = "1"
_os.environ["PYTHONIOENCODING"] = "utf-8"
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
        
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"
TITLE = "BlackKnight"


def _msgbox(text: str, title: str = "BlackKnight", flags: int = 0x10) -> int:
    try:
        return ctypes.windll.user32.MessageBoxW(0, text, title, flags)
    except Exception:
        print(text)
        return 0


def _server_alive() -> bool:
    try:
        with urllib.request.urlopen(URL + "/api/info", timeout=0.7) as r:
            return "model" in json.loads(r.read().decode("utf-8"))
    except Exception:
        return False


def _port_busy() -> bool:
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex((HOST, PORT)) == 0


def _default_size() -> tuple[int, int]:
    try:
        u = ctypes.windll.user32
        w, h = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
        return min(1500, int(w * 0.9)), min(940, int(h * 0.88))
    except Exception:
        return 1280, 820


def start_server():
    if _server_alive():
        return None
    if _port_busy():
        raise RuntimeError(
            f"Port {PORT} is busy by another application.\n"
            f"Close it or launch with another port:\n"
            f"set BK_PORT=9000 && run_desktop.bat"
        )
    cfg = uvicorn.Config(app, host=HOST, port=PORT,
                         log_level="warning", access_log=False)
    server = uvicorn.Server(cfg)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            return server
        time.sleep(0.05)
    raise RuntimeError("Web server did not start within 10 seconds.")


class WindowApi:
    def __init__(self):
        self._window = None
        self._pinned = False
        self._maximized = False
        self._last_max = 0.0

    def bind(self, window):
        self._window = window

    def _hwnd(self):
        try:
            return int(self._window.native.Handle.ToInt64())
        except Exception:
            return None

    def _is_maximized(self) -> bool:
        hwnd = self._hwnd()
        if hwnd and os.name == "nt":
            try:
                return bool(ctypes.windll.user32.IsZoomed(hwnd))
            except Exception:
                pass
        return self._maximized

    def win_state(self):
        return {"maximized": self._is_maximized(), "pinned": self._pinned}

    def win_minimize(self):
        self._window.minimize()

    def win_toggle_max(self):
        t = time.time()
        if t - self._last_max < 0.35:
            return self._is_maximized()
        self._last_max = t
        if self._is_maximized():
            self._window.restore()
            self._maximized = False
        else:
            self._window.maximize()
            self._maximized = True
        return self._maximized

    def win_toggle_pin(self):
        self._pinned = not self._pinned
        self._window.on_top = self._pinned
        return self._pinned

    def win_fullscreen(self):
        self._window.toggle_fullscreen()

    def win_reload(self):
        self._window.load_url(URL)

    def _confirm_close(self) -> bool:
        try:
            running = self._window.evaluate_js(
                "typeof state !== 'undefined' && !!state.running"
            )
            if running and os.name == "nt":
                res = _msgbox(
                    "Агент сейчас выполняет задачу.\n"
                    "Закрыть BlackKnight всё равно?",
                    TITLE, 0x24 | 0x100
                )
                return res == 6
        except Exception:
            pass
        return True

    def win_close(self):
        if self._confirm_close():
            self._window.destroy()


def main():
    try:
        server = start_server()
    except Exception as e:
        _msgbox(f"Cannot start BlackKnight server:\n\n{e}")
        sys.exit(1)

    api = WindowApi()
    width, height = _default_size()

    try:
        window = webview.create_window(
            TITLE, URL,
            width=width, height=height,
            min_size=(1024, 680),
            frameless=True,
            easy_drag=False,
            background_color="#040204",
            js_api=api,
        )
        api.bind(window)

        def on_closing():
            return api._confirm_close()

        def on_closed():
            if server:
                server.should_exit = True

        window.events.closing += on_closing
        window.events.closed += on_closed

        webview.start(debug=os.environ.get("BK_DEBUG") == "1")

        if server:
            server.should_exit = True

    except Exception as e:
        Path("desktop_error.log").write_text(traceback.format_exc(), encoding="utf-8")
        _msgbox(
            "Cannot create BlackKnight desktop window.\n\n"
            "On Windows, install Microsoft Edge WebView2 Runtime:\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
            f"Error: {e}\n"
            "Details: desktop_error.log"
        )
        if server:
            server.should_exit = True
        sys.exit(1)


if __name__ == "__main__":
    main()