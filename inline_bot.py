import os
import time
from typing import Dict, List, Tuple

from pyrogram import Client, filters, idle
from pyrogram.enums import ParseMode
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from inline_core import (
    build_status_text,
    get_api_credentials,
    get_inline_owners,
    list_userbot_commands,
    search_log_text,
    tail_log_text,
)


START_TIME = time.time()
CACHE: Dict[str, Tuple[float, List[InlineQueryResultArticle]]] = {}
CACHE_TTL = 15


def _kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Статус", switch_inline_query_current_chat="status"),
                InlineKeyboardButton("Лог", switch_inline_query_current_chat="log 40"),
            ],
            [
                InlineKeyboardButton("Поиск", switch_inline_query_current_chat="search "),
                InlineKeyboardButton("Команды", switch_inline_query_current_chat="cmds"),
            ],
        ]
    )


def _cache_get(key: str):
    v = CACHE.get(key)
    if not v:
        return None
    ts, payload = v
    if (time.time() - ts) > CACHE_TTL:
        CACHE.pop(key, None)
        return None
    return payload


def _cache_set(key: str, payload):
    CACHE[key] = (time.time(), payload)


def _inline_article(_id: str, title: str, text: str, description: str = ""):
    return InlineQueryResultArticle(
        id=_id,
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
        reply_markup=_kb(),
    )


def _build_results(query: str):
    q = query.strip()
    ql = q.lower()

    if q == "":
        text = tail_log_text(40)
        return [
            _inline_article("log_last", "Последние строки лога", text, "Покажет хвост forelka.log"),
            _inline_article("status", "Статус", build_status_text(START_TIME), "Аптайм и базовое состояние"),
        ]

    if ql == "status":
        return [_inline_article("status", "Статус", build_status_text(START_TIME))]

    if ql.startswith("log"):
        n = 40
        parts = q.split()
        if len(parts) >= 2:
            try:
                n = max(5, min(400, int(parts[1])))
            except Exception:
                n = 40
        return [_inline_article("log", f"Лог ({n})", tail_log_text(n))]

    if ql.startswith("search "):
        needle = q[7:].strip()
        if not needle:
            return [_inline_article("search_empty", "Поиск", "Введите: search <слово>")]
        return [_inline_article("search", f"Поиск: {needle}", search_log_text(needle))]

    if ql in ("cmds", "commands"):
        cmds = list_userbot_commands()
        text = "<b>Команды:</b>\n<blockquote expandable>" + "\n".join(cmds) + "</blockquote>"
        return [_inline_article("cmds", "Команды", text)]

    help_text = (
        "<b>Инлайн</b>\n"
        "<blockquote>"
        "<b>status</b>\n"
        "<b>log [N]</b>\n"
        "<b>search &lt;слово&gt;</b>\n"
        "<b>cmds</b>"
        "</blockquote>"
    )
    return [_inline_article("help", "Помощь", help_text)]


def main():
    token = (os.environ.get("FORELKA_INLINE_TOKEN") or "").strip()
    if not token:
        raise SystemExit("FORELKA_INLINE_TOKEN is empty")

    api_id, api_hash = get_api_credentials()
    owners = get_inline_owners()

    app = Client("forelka-inline", bot_token=token, api_id=api_id, api_hash=api_hash)

    @app.on_inline_query()
    async def _on_inline(_, iq):
        if owners and iq.from_user and iq.from_user.id not in owners:
            await iq.answer([], cache_time=1, is_personal=True)
            return

        key = (iq.query or "").strip()
        cached = _cache_get(key)
        if cached is not None:
            await iq.answer(cached, cache_time=1, is_personal=True)
            return

        results = _build_results(iq.query or "")
        _cache_set(key, results)
        await iq.answer(results, cache_time=1, is_personal=True)

    app.run()


if __name__ == "__main__":
    main()