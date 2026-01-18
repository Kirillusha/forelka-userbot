import asyncio
import html
import os
import json
import sys
import subprocess
import time
import re
import threading
import requests
from typing import Any, Dict, List, Optional, Tuple

from pyrogram import Client
from pyrogram import idle
from pyrogram import filters
from pyrogram import utils
from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler

import loader
from meta_lib import extract_command_descriptions, read_module_meta
from modules import backup as backup_module
import inline_setup

LOG_FILE = "forelka.log"
INLINE_CONFIG_PATH = "inline_bot.json"
RUNTIME_PATH = "runtime.json"
HELP_CACHE_PATH = "inline_help.json"
DEFAULT_CONFIG = {"prefix": "."}
HELP_PAGE_LIMIT = 3200

class TerminalLogger:
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open(LOG_FILE, "a", encoding="utf-8")
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

def _copy_default(value):
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return value


def _load_json(path: str, default):
    if not os.path.exists(path):
        return _copy_default(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data is not None else _copy_default(default)
    except Exception:
        return _copy_default(default)


def _save_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=True)


def load_config(user_id: int) -> Tuple[Dict[str, Any], str]:
    path = f"config-{user_id}.json"
    config = _load_json(path, DEFAULT_CONFIG)
    if "prefix" not in config:
        config["prefix"] = "."
    return config, path


def save_config(path: str, config: Dict[str, Any]) -> None:
    _save_json(path, config)


def load_inline_config(path: str = INLINE_CONFIG_PATH) -> Dict[str, Any]:
    return _load_json(path, {})


def save_inline_config(path: str, config: Dict[str, Any]) -> None:
    _save_json(path, config)


def build_inline_config(token: str, owner_id: int, username: Optional[str] = None) -> Dict[str, Any]:
    data = {
        "token": token,
        "owner_id": owner_id,
        "log_file": LOG_FILE,
        "runtime_file": RUNTIME_PATH,
        "help_file": HELP_CACHE_PATH,
        "created_at": int(time.time()),
    }
    if username:
        data["username"] = username
    return data


def _escape(value: Optional[str]) -> str:
    return html.escape(str(value)) if value is not None else ""


def _first_line(text: Optional[str]) -> str:
    if not text:
        return ""
    return str(text).strip().splitlines()[0].strip()


def _command_descriptions(client, module_name: str, commands: List[str]) -> Dict[str, str]:
    module = sys.modules.get(module_name)
    raw_meta = getattr(module, "__meta__", None) if module else None
    meta_descs = extract_command_descriptions(raw_meta)
    result: Dict[str, str] = {}
    for cmd in commands:
        key = cmd.lower()
        desc = ""
        info = client.commands.get(cmd, {})
        if isinstance(info, dict):
            desc = info.get("description") or info.get("desc") or info.get("about") or info.get("help") or ""
        desc = _first_line(desc)
        if not desc:
            desc = meta_descs.get(key, "")
        if not desc:
            func = client.commands.get(cmd, {}).get("func")
            desc = _first_line(getattr(func, "__doc__", ""))
        result[key] = desc
    return result


def build_inline_help_pages(client) -> List[str]:
    config, _ = load_config(client.me.id)
    pref = config.get("prefix", ".")

    module_cmds: Dict[str, List[str]] = {}
    for cmd_name, info in client.commands.items():
        mod_name = info.get("module", "unknown")
        module_cmds.setdefault(mod_name, []).append(cmd_name)
    for cmds in module_cmds.values():
        cmds.sort()

    module_names = sorted(set(module_cmds.keys()) | set(getattr(client, "loaded_modules", set())))
    blocks: List[str] = []

    for module_name in module_names:
        commands = module_cmds.get(module_name, [])
        module = sys.modules.get(module_name)
        meta = read_module_meta(module, module_name, commands)
        display = meta.get("name") or module_name
        description = _first_line(meta.get("description")) or "No description"
        cmd_descs = _command_descriptions(client, module_name, commands) if commands else {}

        if commands:
            cmd_lines = []
            for cmd in commands:
                desc = cmd_descs.get(cmd.lower()) or "no description"
                cmd_lines.append(f"{pref}{cmd} — {desc}")
            cmds_block = "\n".join(cmd_lines)
        else:
            cmds_block = "No commands"

        block = (
            f"<blockquote><b>{_escape(display)}</b>\n"
            f"{_escape(description)}\n\n"
            f"<code>{_escape(cmds_block)}</code></blockquote>"
        )
        blocks.append(block)

    if not blocks:
        return ["<blockquote>No modules loaded.</blockquote>"]

    pages: List[str] = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > HELP_PAGE_LIMIT and current:
            pages.append(current.strip())
            current = block
        else:
            current = candidate
    if current:
        pages.append(current.strip())
    return pages


def write_help_cache(path: str, pages: List[str], prefix: str) -> None:
    payload = {
        "generated_at": int(time.time()),
        "prefix": prefix,
        "pages": pages,
    }
    _save_json(path, payload)


async def help_cache_loop(client, path: str, interval: int = 120) -> None:
    while True:
        try:
            config, _ = load_config(client.me.id)
            pages = build_inline_help_pages(client)
            write_help_cache(path, pages, config.get("prefix", "."))
        except Exception:
            pass
        await asyncio.sleep(interval)


def format_uptime(seconds: int) -> str:
    minutes, secs = divmod(max(seconds, 0), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts: List[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except Exception:
        return "unknown"


def get_git_branch() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
    except Exception:
        return "unknown"


def get_update_status(branch: str) -> str:
    if not branch or branch == "unknown":
        return "Неизвестно"
    try:
        subprocess.run(
            ["git", "fetch", "origin", branch],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
        result = subprocess.check_output(
            ["git", "rev-list", "--left-right", "--count", f"HEAD...origin/{branch}"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        ahead, behind = (int(x) for x in result.split())
        if behind > 0:
            return "Нужно обновить"
        if ahead > 0:
            return "Локально новее"
        return "Актуальная версия"
    except Exception:
        return "Неизвестно"


def start_inline_bot_thread(config_path: str):
    try:
        import inline_bot as inline_bot_module
    except Exception as e:
        print(f"[inline] failed to import inline bot: {e}")
        return None
    thread = threading.Thread(
        target=inline_bot_module.run_bot, args=(config_path,), daemon=True
    )
    thread.start()
    return thread


async def ensure_inline_bot(client) -> Optional[Dict[str, Any]]:
    inline_cfg = load_inline_config()
    if inline_cfg.get("token"):
        inline_cfg.setdefault("owner_id", client.me.id)
        inline_cfg.setdefault("log_file", LOG_FILE)
        inline_cfg.setdefault("runtime_file", RUNTIME_PATH)
        inline_cfg.setdefault("help_file", HELP_CACHE_PATH)
        save_inline_config(INLINE_CONFIG_PATH, inline_cfg)
        return inline_cfg

    print("Inline bot is not configured.")
    print("Choose inline setup:")
    print("  1) Auto-create via BotFather")
    print("  2) Manual token")
    print("  3) Skip")
    choice = (input("> ").strip() or "2").lower()

    if choice in ("1", "auto", "a"):
        try:
            print("Creating inline bot via BotFather...")
            token, username = await inline_setup.create_inline_bot(client)
            inline_cfg = build_inline_config(token, client.me.id, username=username)
            save_inline_config(INLINE_CONFIG_PATH, inline_cfg)
            print("Inline bot successfully configured.")
            return inline_cfg
        except Exception as e:
            print(f"Inline bot auto-setup failed: {e}")
            return None
    if choice in ("2", "manual", "m"):
        token = input("Inline bot token: ").strip()
        if token:
            inline_cfg = build_inline_config(token, client.me.id)
            save_inline_config(INLINE_CONFIG_PATH, inline_cfg)
            print("Inline bot successfully configured.")
            return inline_cfg
        print("Inline bot token is empty. Skipped.")
        return None

    print("Inline bot setup skipped.")
    return None


async def ensure_log_group(client, config: Dict[str, Any], config_path: str) -> Dict[str, Any]:
    changed = False
    group_id = config.get("log_group_id")

    if group_id:
        try:
            await client.get_chat(group_id)
        except Exception:
            group_id = None

    if not group_id:
        try:
            try:
                chat = await client.create_supergroup(
                    "Forelka Logs",
                    "Logs and backups",
                    is_forum=True,
                )
            except TypeError:
                chat = await client.create_supergroup("Forelka Logs", "Logs and backups")
                try:
                    await client.toggle_forum(chat.id, True)
                except Exception:
                    pass
            group_id = chat.id
            config["log_group_id"] = group_id
            changed = True
        except Exception as e:
            print(f"[logs] Failed to create log group: {e}")
            return config

    async def _ensure_topic(key: str, title: str) -> None:
        nonlocal changed
        if config.get(key):
            return
        try:
            topic = await client.create_forum_topic(group_id, title)
            topic_id = getattr(topic, "message_thread_id", None) or getattr(topic, "id", None)
            if topic_id:
                config[key] = topic_id
                changed = True
        except Exception:
            pass

    if group_id:
        await _ensure_topic("log_topic_backups_id", "Бекапы")
        await _ensure_topic("log_topic_logs_id", "Логи")

    if changed:
        save_config(config_path, config)
    return config


async def send_log_message(client, config: Dict[str, Any], text: str, topic: str = "logs") -> None:
    chat_id = config.get("log_group_id") or "me"
    thread_id = None
    if topic == "logs":
        thread_id = config.get("log_topic_logs_id")
    elif topic == "backups":
        thread_id = config.get("log_topic_backups_id")
    try:
        await client.send_message(
            chat_id,
            text,
            parse_mode=ParseMode.HTML,
            message_thread_id=thread_id,
        )
    except Exception:
        await client.send_message(chat_id, text, parse_mode=ParseMode.HTML)


def _is_alert_line(line: str) -> bool:
    lowered = line.lower()
    triggers = (
        "error",
        "warning",
        "exception",
        "traceback",
        "critical",
        "fatal",
    )
    return any(word in lowered for word in triggers)


async def monitor_log_alerts(client, config: Dict[str, Any]) -> None:
    if not config.get("log_group_id"):
        return
    buffer: List[str] = []
    last_send = time.time()

    while True:
        if not os.path.exists(LOG_FILE):
            await asyncio.sleep(2)
            continue
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if not line:
                        if buffer and (time.time() - last_send) > 4:
                            payload = "\n".join(buffer[-10:])
                            text = (
                                "<b>Forelka Alert</b>\n"
                                f"<blockquote expandable><code>{_escape(payload)}</code></blockquote>"
                            )
                            await send_log_message(client, config, text, topic="logs")
                            buffer.clear()
                            last_send = time.time()
                        await asyncio.sleep(1)
                        continue
                    if _is_alert_line(line):
                        buffer.append(line.strip())
                        if len(buffer) >= 6:
                            payload = "\n".join(buffer[-10:])
                            text = (
                                "<b>Forelka Alert</b>\n"
                                f"<blockquote expandable><code>{_escape(payload)}</code></blockquote>"
                            )
                            await send_log_message(client, config, text, topic="logs")
                            buffer.clear()
                            last_send = time.time()
        except Exception:
            await asyncio.sleep(2)


async def runtime_heartbeat_loop(client, runtime_path: str, payload: Dict[str, Any]) -> None:
    while True:
        payload["last_heartbeat"] = int(time.time())
        _save_json(runtime_path, payload)
        await asyncio.sleep(15)


async def maybe_prompt_auto_backup(client, config: Dict[str, Any], config_path: str) -> None:
    if config.get("auto_backup_hours") or config.get("auto_backup_disabled"):
        return
    if config.get("auto_backup_prompted"):
        return

    text = (
        "<b>Автобекапы</b>\n"
        "<blockquote>У нас присутствует система автоматических бекапов данных.</blockquote>\n"
        "<blockquote>Выберите через сколько часов делать автобекап.</blockquote>\n\n"
        "<b>Примеры:</b> <code>1</code>, <code>2</code>, <code>3</code>, <code>4</code>, <code>6</code>, <code>12</code>\n"
        "<blockquote>Ответьте числом на это сообщение или используйте команду "
        "<code>.autobackup &lt;hours&gt;</code>.</blockquote>"
    )
    inline_cfg = load_inline_config()
    if inline_cfg.get("token") and inline_cfg.get("owner_id"):
        try:
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "1h", "callback_data": "autobackup:set:1"},
                        {"text": "2h", "callback_data": "autobackup:set:2"},
                        {"text": "3h", "callback_data": "autobackup:set:3"},
                    ],
                    [
                        {"text": "4h", "callback_data": "autobackup:set:4"},
                        {"text": "6h", "callback_data": "autobackup:set:6"},
                        {"text": "12h", "callback_data": "autobackup:set:12"},
                    ],
                    [
                        {"text": "Свое значение", "callback_data": "autobackup:custom"},
                        {"text": "Отключить", "callback_data": "autobackup:off"},
                    ],
                ]
            }
            payload = {
                "chat_id": inline_cfg["owner_id"],
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": keyboard,
            }
            resp = requests.post(
                f"https://api.telegram.org/bot{inline_cfg['token']}/sendMessage",
                json=payload,
                timeout=10,
            )
            data = resp.json() if resp.ok else {}
            if data.get("ok"):
                msg_id = data.get("result", {}).get("message_id")
                config["auto_backup_prompted"] = True
                if msg_id:
                    config["auto_backup_prompt_msg_id"] = msg_id
                save_config(config_path, config)
                return
        except Exception:
            pass

    try:
        msg = await client.send_message("me", text, parse_mode=ParseMode.HTML)
        config["auto_backup_prompted"] = True
        config["auto_backup_prompt_msg_id"] = msg.id
        save_config(config_path, config)
    except Exception:
        pass


async def auto_backup_reply_handler(client, message) -> None:
    if not message.text or not message.reply_to_message:
        return
    if message.chat.id != client.me.id:
        return
    config, config_path = load_config(client.me.id)
    prompt_id = config.get("auto_backup_prompt_msg_id")
    if not prompt_id or message.reply_to_message.id != prompt_id:
        return

    raw = message.text.strip().lower()
    if raw in {"off", "нет", "no", "0", "disable"}:
        config["auto_backup_disabled"] = True
        config.pop("auto_backup_hours", None)
        config.pop("auto_backup_next_ts", None)
        config.pop("auto_backup_prompt_msg_id", None)
        save_config(config_path, config)
        await client.send_message("me", "<b>Автобекапы отключены.</b>", parse_mode=ParseMode.HTML)
        return

    try:
        hours = int(raw)
    except ValueError:
        await client.send_message(
            "me",
            "<b>Неверное значение.</b>\n<blockquote>Введите число часов, например <code>2</code>.</blockquote>",
            parse_mode=ParseMode.HTML,
        )
        return

    if hours <= 0:
        await client.send_message(
            "me",
            "<b>Неверное значение.</b>\n<blockquote>Часы должны быть больше нуля.</blockquote>",
            parse_mode=ParseMode.HTML,
        )
        return

    config["auto_backup_hours"] = hours
    config["auto_backup_next_ts"] = int(time.time() + hours * 3600)
    config.pop("auto_backup_prompt_msg_id", None)
    config.pop("auto_backup_disabled", None)
    save_config(config_path, config)
    await client.send_message(
        "me",
        f"<b>Автобекапы включены.</b>\n<blockquote>Интервал: <code>{hours}h</code></blockquote>",
        parse_mode=ParseMode.HTML,
    )


async def run_auto_backup(client, config: Dict[str, Any], config_path: str) -> None:
    try:
        backup_path, files = backup_module.create_backup_archive()
    except Exception as e:
        await send_log_message(
            client,
            config,
            f"<b>Auto backup failed:</b> <code>{_escape(str(e))}</code>",
            topic="logs",
        )
        return

    caption = backup_module.build_backup_caption(backup_path, files, title="Auto backup")
    chat_id = config.get("log_group_id") or "me"
    thread_id = config.get("log_topic_backups_id")
    try:
        await client.send_document(
            chat_id,
            document=backup_path,
            caption=caption,
            parse_mode=ParseMode.HTML,
            message_thread_id=thread_id,
        )
    except Exception:
        await client.send_document(
            chat_id,
            document=backup_path,
            caption=caption,
            parse_mode=ParseMode.HTML,
        )


async def auto_backup_loop(client, config_path: str) -> None:
    while True:
        config, _ = load_config(client.me.id)
        hours = config.get("auto_backup_hours")
        try:
            hours_int = int(hours) if hours else 0
        except Exception:
            hours_int = 0
        if hours_int:
            next_ts = config.get("auto_backup_next_ts")
            now = time.time()
            if not next_ts or now >= next_ts:
                await run_auto_backup(client, config, config_path)
                config["auto_backup_next_ts"] = int(now + hours_int * 3600)
                save_config(config_path, config)
        await asyncio.sleep(60)

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
    # Обработчик ответов на настройку автобекапов
    client.add_handler(MessageHandler(auto_backup_reply_handler, filters.me & filters.text))

    await client.start()
    client.start_time = time.time()
    loader.load_all(client)

    config, config_path = load_config(client.me.id)
    client.prefix = config.get("prefix", ".")

    config = await ensure_log_group(client, config, config_path)

    branch = get_git_branch()
    git_commit = get_git_commit()
    update_status = get_update_status(branch)

    runtime_payload = {
        "start_time": int(client.start_time),
        "last_heartbeat": int(time.time()),
        "git_commit": git_commit,
        "git_branch": branch,
        "update_status": update_status,
    }
    _save_json(RUNTIME_PATH, runtime_payload)
    asyncio.create_task(runtime_heartbeat_loop(client, RUNTIME_PATH, runtime_payload))

    pages = build_inline_help_pages(client)
    write_help_cache(HELP_CACHE_PATH, pages, config.get("prefix", "."))
    asyncio.create_task(help_cache_loop(client, HELP_CACHE_PATH))

    inline_cfg = await ensure_inline_bot(client)
    if inline_cfg:
        client.inline_bot_thread = start_inline_bot_thread(INLINE_CONFIG_PATH)

    await maybe_prompt_auto_backup(client, config, config_path)
    asyncio.create_task(auto_backup_loop(client, config_path))
    asyncio.create_task(monitor_log_alerts(client, config))

    startup_text = (
        "<b>Forelka Userbot started!</b>\n\n"
        f"<blockquote><b>Commit:</b> <code>{_escape(git_commit)}</code></blockquote>\n"
        f"<blockquote><b>Update status:</b> <code>{_escape(update_status)}</code></blockquote>\n"
        f"<blockquote expandable><b>Uptime:</b> <code>{format_uptime(0)}</code></blockquote>"
    )
    await send_log_message(client, config, startup_text, topic="logs")

    print(fr"""
  __               _ _         
 / _|             | | |        
| |_ ___  _ __ ___| | | ____ _ 
|  _/ _ \| '__/ _ \ | |/ / _` |
| || (_) | | |  __/ |   < (_| |
|_| \___/|_|  \___|_|_|\_\__,_|

Forelka Started | Git: #{git_commit}
""")

    await idle()

if __name__ == "__main__":
    asyncio.run(main())
