import asyncio
import json
import os
import random
import re
import string
import sys
import time

from pyrogram.enums import ParseMode

BOTFATHER_USERNAME = "BotFather"
INLINE_PLACEHOLDER = "user@forelka:~$"
TOKEN_RE = re.compile(r"\d{6,}:[\w-]{30,}")
FORELKA_BOT_RE = re.compile(r"@forelka_[0-9a-zA-Z]{6}_bot")
MAX_USERNAME_TRIES = 5
INLINE_BOT_SCRIPT = "inline_bot.py"


def _load_config(path):
    cfg = {"prefix": "."}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    return cfg


def _save_config(path, cfg):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


def _normalize_username(value):
    if not value:
        return None
    value = value.strip()
    if value.startswith("@"):
        value = value[1:]
    return value or None


def _mask_token(token):
    if not token:
        return ""
    if len(token) < 12:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


async def _start_inline_bot_process(client, restart=False):
    script_path = os.path.join(os.getcwd(), INLINE_BOT_SCRIPT)
    if not os.path.exists(script_path):
        return False, "inline_bot.py not found"

    proc = getattr(client, "_inline_bot_process", None)
    if proc and proc.returncode is None:
        if not restart:
            return False, "already running"
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=5)
        except Exception:
            pass

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            script_path,
            cwd=os.getcwd(),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        client._inline_bot_process = proc
        return True, "started"
    except Exception as e:
        return False, str(e)


class BotFatherInlineManager:
    def __init__(self, client):
        self.client = client
        self.config_path = f"config-{client.me.id}.json"
        self.config = _load_config(self.config_path)

    def _refresh_config(self):
        self.config = _load_config(self.config_path)

    def _set_config_value(self, key, value):
        self.config[key] = value
        _save_config(self.config_path, self.config)

    def _get_config_value(self, key, default=None):
        return self.config.get(key, default)

    def get_token(self):
        return self._get_config_value("inline_bot_token")

    def get_username(self):
        return self._get_config_value("inline_bot_username")

    def set_username(self, username):
        self._set_config_value("inline_bot_username", username)

    def clear_token(self):
        if "inline_bot_token" in self.config:
            self.config.pop("inline_bot_token", None)
            _save_config(self.config_path, self.config)

    async def _throttle(self):
        await asyncio.sleep(0.8)

    async def _send_and_wait(self, text, timeout=45):
        sent = await self.client.send_message(BOTFATHER_USERNAME, text)
        return await self._wait_for_response(sent.id, timeout=timeout)

    async def _wait_for_response(self, after_id, timeout=45):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            async for msg in self.client.get_chat_history(BOTFATHER_USERNAME, limit=6):
                if msg.id <= after_id:
                    break
                from_user = getattr(msg, "from_user", None)
                username = (getattr(from_user, "username", "") or "").lower()
                if username == BOTFATHER_USERNAME.lower():
                    return msg
            await asyncio.sleep(0.6)
        raise TimeoutError("BotFather did not respond in time")

    def _extract_token(self, text):
        if not text:
            return None
        match = TOKEN_RE.search(text)
        return match.group(0) if match else None

    def _extract_buttons(self, message):
        markup = getattr(message, "reply_markup", None)
        if not markup:
            return []

        rows = None
        if hasattr(markup, "keyboard"):
            rows = markup.keyboard
        elif hasattr(markup, "inline_keyboard"):
            rows = markup.inline_keyboard
        elif hasattr(markup, "rows"):
            rows = markup.rows

        if not rows:
            return []

        buttons = []
        for row in rows:
            items = row.buttons if hasattr(row, "buttons") else row
            for button in items:
                text = getattr(button, "text", None)
                if text:
                    buttons.append(text.strip())
        return buttons

    def _pick_username_from_buttons(self, buttons):
        custom = _normalize_username(self.get_username())
        if custom:
            for button in buttons:
                if button.strip("@") == custom:
                    return f"@{custom}"
            return None

        for button in buttons:
            if FORELKA_BOT_RE.search(button):
                return button if button.startswith("@") else f"@{button}"
        return None

    def _generate_username(self):
        suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        return f"forelka_{suffix}_bot"

    async def _set_inline(self, username):
        await self._send_and_wait("/setinline")
        await self._throttle()
        await self._send_and_wait(username)
        await self._throttle()
        await self._send_and_wait(INLINE_PLACEHOLDER)
        await self._throttle()
        await self._send_and_wait("/setinlinefeedback")
        await self._throttle()
        await self._send_and_wait(username)
        await self._throttle()
        await self._send_and_wait("Enabled")

    async def _request_token_for_bot(self, username, revoke_token=False):
        response = await self._send_and_wait(username)
        await self._throttle()

        if revoke_token:
            await self._send_and_wait("/revoke")
            await self._throttle()
            response = await self._send_and_wait(username)
            await self._throttle()

        token = self._extract_token(response.text or "")

        if not token:
            return None

        normalized = _normalize_username(username)
        self._set_config_value("inline_bot_token", token)
        self._set_config_value("inline_bot_username", normalized)
        await self._set_inline(f"@{normalized}")
        return token

    async def _create_bot(self):
        response = await self._send_and_wait("/newbot")
        await self._throttle()
        if response.text and "20" in response.text:
            return None

        await self._send_and_wait("Forelka Userbot")
        await self._throttle()

        custom = _normalize_username(self.get_username())
        for attempt in range(MAX_USERNAME_TRIES):
            username = custom if (attempt == 0 and custom) else self._generate_username()
            response = await self._send_and_wait(f"@{username}")
            await self._throttle()

            text = (response.text or "").lower()
            if "sorry" in text or "invalid" in text or "taken" in text:
                if custom:
                    custom = None
                continue

            token = self._extract_token(response.text or "")
            if not token and ("done" in text or "congratulations" in text):
                token = await self._request_token_for_bot(f"@{username}")
                if token:
                    return token
            if token:
                self._set_config_value("inline_bot_token", token)
                self._set_config_value("inline_bot_username", username)
                await self._set_inline(f"@{username}")
                return token

        return None

    async def ensure_token(self, create_new=True, revoke_token=False):
        if not revoke_token:
            token = self.get_token()
            if token:
                return token

        response = await self._send_and_wait("/token")
        await self._throttle()
        buttons = self._extract_buttons(response)
        if not buttons:
            return await self._create_bot() if create_new else None

        username = self._pick_username_from_buttons(buttons)
        if not username:
            return await self._create_bot() if create_new else None

        token = await self._request_token_for_bot(username, revoke_token=revoke_token)
        return token


async def inlinebot_cmd(client, message, args):
    """Setup and manage inline bot token via BotFather."""
    manager = BotFatherInlineManager(client)
    pref = _load_config(manager.config_path).get("prefix", ".")

    if not args:
        token = manager.get_token()
        username = manager.get_username() or "not set"
        status = "✅ настроен" if token else "❌ не найден"
        proc = getattr(client, "_inline_bot_process", None)
        running = proc and proc.returncode is None
        runtime = "🟢 запущен" if running else "⚪ не запущен"
        text = (
            "<blockquote><emoji id=5897962422169243693>👻</emoji> <b>Inline Bot</b></blockquote>\n\n"
            f"<b>Статус:</b> <code>{status}</code>\n"
            f"<b>Username:</b> <code>{username}</code>\n"
            f"<b>Token:</b> <code>{_mask_token(token) or '—'}</code>\n"
            f"<b>Inline bot:</b> <code>{runtime}</code>\n\n"
            "<b>Команды:</b>\n"
            f"<code>{pref}inlinebot setup</code> - создать или получить токен\n"
            f"<code>{pref}inlinebot revoke</code> - перевыпустить токен\n"
            f"<code>{pref}inlinebot token</code> - показать токен\n"
            f"<code>{pref}inlinebot set @username</code> - задать кастомный бот\n"
            f"<code>{pref}inlinebot clear</code> - удалить токен из конфига"
        )
        return await message.edit(text, parse_mode=ParseMode.HTML)

    sub = args[0].lower()

    if sub in {"set", "username"}:
        if len(args) < 2:
            return await message.edit(
                f"<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage:</b> <code>{pref}inlinebot set @username</code></blockquote>",
                parse_mode=ParseMode.HTML,
            )
        username = _normalize_username(args[1])
        if not username:
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Неверный username</b></blockquote>",
                parse_mode=ParseMode.HTML,
            )
        manager.set_username(username)
        return await message.edit(
            f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Username сохранен:</b> <code>@{username}</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    if sub in {"clear", "reset"}:
        manager.clear_token()
        return await message.edit(
            "<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Токен удален из конфига</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    if sub in {"token", "show"}:
        token = manager.get_token()
        if not token:
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Токен не найден. Запустите setup</b></blockquote>",
                parse_mode=ParseMode.HTML,
            )
        return await message.edit(
            f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Token:</b> <code>{token}</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    if sub in {"setup", "create", "start"}:
        await message.edit(
            "<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Создаю/проверяю токен...</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )
        try:
            token = await manager.ensure_token(create_new=True, revoke_token=False)
        except Exception as e:
            return await message.edit(
                f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>",
                parse_mode=ParseMode.HTML,
            )

        if not token:
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Не удалось получить токен</b></blockquote>",
                parse_mode=ParseMode.HTML,
            )

        started, start_msg = await _start_inline_bot_process(client, restart=False)
        username = manager.get_username() or "unknown"
        runtime = "🟢 запущен" if started or start_msg == "already running" else "⚠️ не запущен"
        runtime_note = "" if started or start_msg == "already running" else f"\n<b>Причина:</b> <code>{start_msg}</code>"
        return await message.edit(
            "<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Token получен!</b></blockquote>\n\n"
            f"<b>Username:</b> <code>@{username}</code>\n"
            f"<b>Token:</b> <code>{token}</code>\n\n"
            f"<b>Inline bot:</b> <code>{runtime}</code>{runtime_note}",
            parse_mode=ParseMode.HTML,
        )

    if sub in {"revoke", "refresh"}:
        await message.edit(
            "<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Перевыпускаю токен...</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )
        try:
            token = await manager.ensure_token(create_new=True, revoke_token=True)
        except Exception as e:
            return await message.edit(
                f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>",
                parse_mode=ParseMode.HTML,
            )

        if not token:
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Не удалось перевыпустить токен</b></blockquote>",
                parse_mode=ParseMode.HTML,
            )

        started, start_msg = await _start_inline_bot_process(client, restart=True)
        username = manager.get_username() or "unknown"
        runtime = "🟢 перезапущен" if started or start_msg == "already running" else "⚠️ не запущен"
        runtime_note = "" if started or start_msg == "already running" else f"\n<b>Причина:</b> <code>{start_msg}</code>"
        return await message.edit(
            "<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Token обновлен!</b></blockquote>\n\n"
            f"<b>Username:</b> <code>@{username}</code>\n"
            f"<b>Token:</b> <code>{token}</code>\n\n"
            f"<b>Inline bot:</b> <code>{runtime}</code>{runtime_note}",
            parse_mode=ParseMode.HTML,
        )

    return await message.edit(
        f"<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage:</b> <code>{pref}inlinebot</code></blockquote>",
        parse_mode=ParseMode.HTML,
    )


def register(app, commands, module_name):
    commands["inlinebot"] = {"func": inlinebot_cmd, "module": module_name}
    commands["inline"] = {"func": inlinebot_cmd, "module": module_name}
