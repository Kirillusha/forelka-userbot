import asyncio
import random
import re
import string
import time
from typing import Optional, Tuple

BOTFATHER_CHAT = "BotFather"
TOKEN_RE = re.compile(r"\b\d{8,}:[A-Za-z0-9_-]{30,}\b")
USERNAME_RE = re.compile(r"@([A-Za-z0-9_]{5,32}bot)\b", re.IGNORECASE)


def _generate_username(prefix: str = "forelka_inline") -> str:
    suffix = "".join(random.choices(string.digits, k=5))
    base = f"{prefix}_{suffix}_bot"
    return base[:32]


async def _fetch_latest_message(client, chat_id: str):
    if hasattr(client, "get_chat_history"):
        try:
            history = await client.get_chat_history(chat_id, limit=1)
            if isinstance(history, list):
                return history[0] if history else None
            async for msg in history:
                return msg
            return None
        except TypeError:
            history = client.get_chat_history(chat_id, limit=1)
            async for msg in history:
                return msg
            return None
    if hasattr(client, "get_history"):
        try:
            history = await client.get_history(chat_id, limit=1)
            return history[0] if history else None
        except TypeError:
            history = client.get_history(chat_id, limit=1)
            async for msg in history:
                return msg
            return None
    if hasattr(client, "iter_history"):
        history = client.iter_history(chat_id, limit=1)
        async for msg in history:
            return msg
    return None


async def _get_last_message_id(client, chat_id: str) -> int:
    message = await _fetch_latest_message(client, chat_id)
    return message.id if message else 0


async def _wait_new_message(client, chat_id: str, last_id: int, timeout: int = 90):
    start = time.time()
    while time.time() - start < timeout:
        message = await _fetch_latest_message(client, chat_id)
        if message and message.id != last_id:
            return message
        await asyncio.sleep(1)
    raise TimeoutError("BotFather did not respond in time")


async def _enable_inline_mode(client, username: str) -> None:
    last_id = await _get_last_message_id(client, BOTFATHER_CHAT)
    await client.send_message(BOTFATHER_CHAT, "/setinline")
    msg = await _wait_new_message(client, BOTFATHER_CHAT, last_id)

    last_id = msg.id
    await client.send_message(BOTFATHER_CHAT, f"@{username.lstrip('@')}")
    msg = await _wait_new_message(client, BOTFATHER_CHAT, last_id)

    last_id = msg.id
    await client.send_message(BOTFATHER_CHAT, "Search logs, status, help")
    await _wait_new_message(client, BOTFATHER_CHAT, last_id)


async def create_inline_bot(
    client,
    display_name: str = "Forelka Inline Bot",
    username_prefix: str = "forelka_inline",
    attempts: int = 5,
) -> Tuple[str, str]:
    last_id = await _get_last_message_id(client, BOTFATHER_CHAT)
    await client.send_message(BOTFATHER_CHAT, "/newbot")
    msg = await _wait_new_message(client, BOTFATHER_CHAT, last_id)

    last_id = msg.id
    await client.send_message(BOTFATHER_CHAT, display_name)
    msg = await _wait_new_message(client, BOTFATHER_CHAT, last_id)

    token: Optional[str] = None
    username: Optional[str] = None

    for _ in range(attempts):
        candidate = _generate_username(username_prefix)
        last_id = msg.id
        await client.send_message(BOTFATHER_CHAT, candidate)
        msg = await _wait_new_message(client, BOTFATHER_CHAT, last_id)

        token_match = TOKEN_RE.search(msg.text or "")
        if token_match:
            token = token_match.group(0)
            username_match = USERNAME_RE.search(msg.text or "")
            username = username_match.group(1) if username_match else candidate
            break

        text = (msg.text or "").lower()
        if "already" in text or "taken" in text or "invalid" in text:
            continue

    if not token or not username:
        raise RuntimeError("Failed to create inline bot via BotFather")

    await _enable_inline_mode(client, username)
    return token, username
