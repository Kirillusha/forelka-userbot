import asyncio
import os
import json
import sys
import subprocess
import time
import re
import threading

from pyrogram import Client
from pyrogram import idle
from pyrogram import filters
from pyrogram import utils
from pyrogram.handlers import MessageHandler

import loader

class TerminalLogger:
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("forelka.log", "a", encoding="utf-8")
        self.ignore_list = [
            "PERSISTENT_TIMESTAMP_OUTDATED",
            "updates.GetChannelDifference",
            "RPC_CALL_FAIL",
            "Retrying \"updates.GetChannelDifference\""
        ]
        
    def write(self, m):
        if not m.strip():
            return
        if any(x in m for x in self.ignore_list):
            return
        self.terminal.write(m)
        self.log.write(m)
        self.log.flush()
        try:
            self.terminal.flush()
        except Exception:
            pass
        
    def flush(self): 
        try:
            self.log.flush()
        except Exception:
            pass
        try:
            self.terminal.flush()
        except Exception:
            pass

sys.stdout = sys.stderr = TerminalLogger()

def load_saved_api_for_session(session_filename: str):
    """
    Пытается прочитать api_id/api_hash, сохранённые веб-логином (или вручную),
    чтобы Client мог стартовать даже если библиотека требует эти параметры.
    """
    # session_filename: forelka-<id>.session
    try:
        base = session_filename[:-8]  # forelka-<id>
        user_id = int(base.split("-", 1)[1])
    except Exception:
        return None

    path = f"telegram_api-{user_id}.json"
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        api_id = int(data["api_id"])
        api_hash = str(data["api_hash"])
        if not api_hash:
            return None
        return api_id, api_hash
    except Exception:
        return None

def _list_session_files():
    try:
        return sorted(
            [f for f in os.listdir() if f.startswith("forelka-") and f.endswith(".session")],
            key=lambda p: os.path.getmtime(p),
        )
    except Exception:
        return []

def _pick_latest_session():
    sess = _list_session_files()
    return sess[-1] if sess else None

async def _terminal_login_create_session():
    api_id, api_hash = input("API ID: "), input("API HASH: ")
    temp = Client("temp", api_id=api_id, api_hash=api_hash)
    await temp.start()
    me = await temp.get_me()
    await temp.stop()
    os.rename("temp.session", f"forelka-{me.id}.session")
    return f"forelka-{me.id}.session"

def _watch_process_output_for_url(proc: subprocess.Popen, label: str):
    """
    Читает stdout процесса и вытаскивает публичный URL. По умолчанию НЕ спамит stdout,
    чтобы в терминале было удобно (особенно из-за ASCII QR/баннеров localhost.run).
    Работает в отдельном потоке.
    """
    url_re = re.compile(r"(https?://[a-zA-Z0-9.-]+\.(?:localhost\.run|lhr\.life))")
    found = {"url": None}
    verbose = os.environ.get("FORELKA_TUNNEL_VERBOSE", "").strip() in ("1", "true", "yes", "on")

    def run():
        try:
            if proc.stdout is None:
                return
            for line in proc.stdout:
                if verbose:
                    try:
                        sys.stdout.write(f"[{label}] {line}")
                    except Exception:
                        pass
                m = url_re.search(line)
                if m and not found["url"]:
                    url = m.group(1)
                    if "admin.localhost.run" in url or "localhost.run/docs" in url:
                        continue
                    found["url"] = url
                    print(f"\nPublic URL: {found['url']}\n")
        except Exception:
            pass

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return found

async def _web_login_create_session(with_tunnel: bool = False):
    before = set(_list_session_files())

    host = os.environ.get("FORELKA_WEB_HOST", "127.0.0.1")
    port = os.environ.get("FORELKA_WEB_PORT", "8000")
    print(f"Web panel: http://{host}:{port}")

    # Запускаем отдельным процессом, чтобы можно было корректно остановить после логина
    proc = subprocess.Popen(
        [sys.executable, "webapp.py"],
        env={**os.environ, "FORELKA_WEB_HOST": host, "FORELKA_WEB_PORT": str(port)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    tunnel_proc = None
    if with_tunnel:
        try:
            tunnel_proc = subprocess.Popen(
                [sys.executable, "-u", "tunnel.py"],
                env={
                    **os.environ,
                    "FORELKA_WEB_HOST": host,
                    "FORELKA_WEB_PORT": str(port),
                    # По умолчанию просим tunnel.py быть тихим (печатает только URL).
                    "FORELKA_TUNNEL_QUIET": "1",
                    # На всякий случай отключаем буферизацию python stdout
                    "PYTHONUNBUFFERED": "1",
                },
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            _watch_process_output_for_url(tunnel_proc, "tunnel")
        except Exception as e:
            print(f"[tunnel] Failed to start tunnel: {e}")
            tunnel_proc = None

    try:
        # Ждём появления новой сессии
        while True:
            await asyncio.sleep(0.6)
            now = set(_list_session_files())
            created = [s for s in now - before]
            if created:
                # Если создано несколько, берём самую свежую
                created.sort(key=lambda p: os.path.getmtime(p))
                return created[-1], proc, tunnel_proc

            # Если webapp упал — прекращаем ожидание
            if proc.poll() is not None:
                raise RuntimeError("web login server stopped unexpectedly")
    except KeyboardInterrupt:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            pass
        if tunnel_proc:
            try:
                tunnel_proc.terminate()
                tunnel_proc.wait(timeout=5)
            except Exception:
                pass
        raise

def is_owner(client, user_id):
    """Проверяет является ли пользователь овнером"""
    path = f"config-{client.me.id}.json"
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                config = json.load(f)
                owners = config.get("owners", [])
                return user_id in owners
        except:
            pass
    return False

async def handler(c, m):
    """Обработчик команд от самого юзербота"""
    if not m.text: 
        return
    path = f"config-{c.me.id}.json"
    pref = "."
    if os.path.exists(path):
        try:
            with open(path, "r") as f: 
                pref = json.load(f).get("prefix", ".")
        except: 
            pass
    if not m.text.startswith(pref): 
        return
    parts = m.text[len(pref):].split(maxsplit=1)
    if not parts: 
        return
    cmd = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []
    if cmd in c.commands:
        try: 
            await c.commands[cmd]["func"](c, m, args)
        except: 
            pass

async def owner_handler(c, m):
    """Обработчик команд от овнеров - юзербот выполняет команду от своего имени"""
    if not m.text or not m.from_user:
        return
    
    # Проверяем что это овнер
    if not is_owner(c, m.from_user.id):
        return
    
    path = f"config-{c.me.id}.json"
    pref = "."
    if os.path.exists(path):
        try:
            with open(path, "r") as f: 
                pref = json.load(f).get("prefix", ".")
        except: 
            pass
    
    if not m.text.startswith(pref): 
        return
    
    parts = m.text[len(pref):].split(maxsplit=1)
    if not parts: 
        return
    
    cmd = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []
    
    if cmd in c.commands:
        try:
            # Юзербот отправляет команду от своего имени
            sent_msg = await c.send_message(m.chat.id, m.text)
            # Выполняем команду
            await c.commands[cmd]["func"](c, sent_msg, args)
        except Exception as e:
            pass

async def edited_handler(c, m):
    """Обработчик отредактированных сообщений"""
    await handler(c, m)

async def main():
    utils.get_peer_type = lambda x: "channel" if str(x).startswith("-100") else ("chat" if x < 0 else "user")

    sess = _pick_latest_session()
    web_proc = None
    tunnel_proc = None

    if not sess:
        print("No session found.")
        print("Choose login method:")
        print("  1) Terminal (API ID/HASH + phone in terminal)/n")
        print("  2) Web panel (HTML login page)")
        print("  3) Web + tunnel (HTML + public localhost.run URL)")
        choice = (input("> ").strip() or "2").lower()

        if choice in ("1", "t", "term", "terminal"):
            sess = await _terminal_login_create_session()
        elif choice in ("2", "w", "web"):
            sess, web_proc, tunnel_proc = await _web_login_create_session(with_tunnel=False)
        elif choice in ("3", "wt", "web+tunnel", "web+t"):
            sess, web_proc, tunnel_proc = await _web_login_create_session(with_tunnel=True)
        else:
            print("Cancelled.")
            return

    # Если web login был выбран — аккуратно завершаем webapp и продолжаем запуск без перезагрузки
    if web_proc:
        try:
            web_proc.terminate()
            web_proc.wait(timeout=5)
        except Exception:
            pass
    if tunnel_proc:
        try:
            tunnel_proc.terminate()
            tunnel_proc.wait(timeout=5)
        except Exception:
            pass

    api = load_saved_api_for_session(sess)
    try:
        if api:
            client = Client(sess[:-8], api_id=api[0], api_hash=api[1])
        else:
            client = Client(sess[:-8])
    except TypeError:
        api_id, api_hash = input("API ID: "), input("API HASH: ")
        client = Client(sess[:-8], api_id=api_id, api_hash=api_hash)

    client.commands = {}
    client.loaded_modules = set()
    # Обработчик для команд от самого юзербота
    client.add_handler(MessageHandler(handler, filters.me & filters.text))
    # Обработчик для команд от овнеров
    client.add_handler(MessageHandler(owner_handler, ~filters.me & filters.text))
    # Обработчик для отредактированных сообщений
    from pyrogram.handlers import EditedMessageHandler
    client.add_handler(EditedMessageHandler(edited_handler, filters.me & filters.text))

    await client.start()
    client.start_time = time.time()
    loader.load_all(client)

    git = "unknown"
    try: 
        git = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except: 
        pass

    print(fr"""
  __               _ _         
 / _|             | | |        
| |_ ___  _ __ ___| | | ____ _ 
|  _/ _ \| '__/ _ \ | |/ / _` |
| || (_) | | |  __/ |   < (_| |
|_| \___/|_|  \___|_|_|\_\__,_|

Forelka Started | Git: #{git}
""")

    await idle()

if __name__ == "__main__":
    asyncio.run(main())
