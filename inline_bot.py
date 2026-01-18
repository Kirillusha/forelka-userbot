import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
)

DEFAULT_CONFIG_PATH = os.environ.get("FORELKA_INLINE_CONFIG", "inline_bot.json")
DEFAULT_LOG_FILE = "forelka.log"
DEFAULT_RUNTIME_FILE = "runtime.json"
DEFAULT_HELP_FILE = "inline_help.json"

RUNTIME_CACHE_TTL = 2
HELP_CACHE_TTL = 6
INLINE_CACHE_TTL = 20


class JsonCache:
    def __init__(self, path: str, ttl: int):
        self.path = path
        self.ttl = ttl
        self._data: Optional[Dict[str, Any]] = None
        self._loaded_at = 0.0

    def read(self) -> Dict[str, Any]:
        now = time.time()
        if self._data is not None and (now - self._loaded_at) < self.ttl:
            return self._data
        self._loaded_at = now
        if not os.path.exists(self.path):
            self._data = {}
            return self._data
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = json.load(f) or {}
        except Exception:
            self._data = {}
        return self._data


def _format_uptime(seconds: int) -> str:
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


def _read_log_lines(path: str, num_lines: int = 20) -> str:
    if not os.path.exists(path):
        return "Лог-файл отсутствует."
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-num_lines:]).strip() or "Лог пуст."
    except Exception:
        return "Не удалось прочитать лог."


def _search_logs(path: str, keyword: str, max_results: int = 10) -> str:
    if not os.path.exists(path):
        return "Лог-файл отсутствует."
    keyword = keyword.lower().strip()
    if not keyword:
        return "Введите ключевое слово для поиска."
    found: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if keyword in line.lower():
                    found.append(line.strip())
                    if len(found) >= max_results:
                        break
    except Exception:
        return "Не удалось выполнить поиск в логе."
    if not found:
        return f"По запросу '{keyword}' ничего не найдено."
    return "\n".join(found)


def _load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError("Inline bot config not found")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    if not data.get("token") or not data.get("owner_id"):
        raise ValueError("Inline bot config is incomplete")
    data.setdefault("log_file", DEFAULT_LOG_FILE)
    data.setdefault("runtime_file", DEFAULT_RUNTIME_FILE)
    data.setdefault("help_file", DEFAULT_HELP_FILE)
    return data


def _build_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статус", callback_data="nav:status"),
                InlineKeyboardButton(text="📶 Пинг", callback_data="nav:ping"),
            ],
            [
                InlineKeyboardButton(text="📚 Помощь", callback_data="help:page:0"),
                InlineKeyboardButton(text="🧾 Логи", callback_data="nav:logs"),
            ],
            [InlineKeyboardButton(text="🧰 Автобекапы", callback_data="nav:autobackup")],
        ]
    )


def _build_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧾 Последние строки", switch_inline_query_current_chat=""
                ),
                InlineKeyboardButton(
                    text="🔍 Поиск", switch_inline_query_current_chat="search "
                ),
            ],
            [
                InlineKeyboardButton(text="📊 Статус", switch_inline_query_current_chat="status"),
                InlineKeyboardButton(text="📚 Помощь", switch_inline_query_current_chat="help"),
            ],
        ]
    )


def _build_help_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    row: List[InlineKeyboardButton] = []
    if total_pages > 1:
        if page > 0:
            row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"help:page:{page - 1}"))
        row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            row.append(InlineKeyboardButton("➡️ Далее", callback_data=f"help:page:{page + 1}"))
    keyboard_rows: List[List[InlineKeyboardButton]] = []
    if row:
        keyboard_rows.append(row)
    keyboard_rows.append([InlineKeyboardButton("✖️ Закрыть", callback_data="help:close")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def _build_config_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="nav:config"),
                InlineKeyboardButton(text="📚 Помощь", callback_data="help:page:0"),
            ],
            [InlineKeyboardButton(text="✖️ Закрыть", callback_data="help:close")],
        ]
    )


def _build_status_text(runtime: Dict[str, Any]) -> str:
    now = time.time()
    start_time = int(runtime.get("start_time") or 0)
    heartbeat = int(runtime.get("last_heartbeat") or 0)
    uptime = _format_uptime(int(now - start_time)) if start_time else "unknown"
    heartbeat_age = int(now - heartbeat) if heartbeat else None
    status = "Онлайн" if heartbeat_age is not None and heartbeat_age <= 90 else "Оффлайн"
    commit = runtime.get("git_commit", "unknown")
    update_status = runtime.get("update_status", "unknown")

    blocks = [
        "<blockquote><b>Статус:</b> <code>{}</code></blockquote>".format(status),
        "<blockquote><b>Аптайм:</b> <code>{}</code></blockquote>".format(uptime),
        "<blockquote><b>Коммит:</b> <code>{}</code></blockquote>".format(commit),
        "<blockquote><b>Обновление:</b> <code>{}</code></blockquote>".format(update_status),
    ]
    if heartbeat_age is not None:
        blocks.insert(
            2,
            "<blockquote><b>Сердцебиение:</b> <code>{}s назад</code></blockquote>".format(
                heartbeat_age
            ),
        )

    return "<b>Forelka Inline Control</b>\n\n" + "\n".join(blocks)


def _build_ping_text(runtime: Dict[str, Any]) -> str:
    now = time.time()
    heartbeat = int(runtime.get("last_heartbeat") or 0)
    if not heartbeat:
        return "<b>Пинг</b>\n<blockquote><b>Статус:</b> <code>нет данных</code></blockquote>"
    delta = int(now - heartbeat)
    status = "Онлайн" if delta <= 90 else "Оффлайн"
    return (
        "<b>Пинг</b>\n"
        "<blockquote><b>Статус:</b> <code>{}</code></blockquote>\n"
        "<blockquote><b>Последнее сердцебиение:</b> <code>{}s назад</code></blockquote>"
    ).format(status, delta)


def _format_ts(timestamp: Optional[int]) -> str:
    if not timestamp:
        return "—"
    return time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(int(timestamp)))


def _build_autobackup_text(config: Dict[str, Any]) -> str:
    hours = config.get("auto_backup_hours")
    next_ts = config.get("auto_backup_next_ts")
    status = "Отключены"
    if hours:
        status = f"Каждые {hours}h"
    return (
        "<b>Автобекапы</b>\n"
        f"<blockquote><b>Статус:</b> <code>{status}</code>\n"
        f"<b>Следующий:</b> <code>{_format_ts(next_ts)}</code></blockquote>\n"
        "<blockquote>Выберите интервал или задайте своё значение.</blockquote>"
    )


def _build_autobackup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("1h", callback_data="autobackup:set:1"),
                InlineKeyboardButton("2h", callback_data="autobackup:set:2"),
                InlineKeyboardButton("3h", callback_data="autobackup:set:3"),
            ],
            [
                InlineKeyboardButton("4h", callback_data="autobackup:set:4"),
                InlineKeyboardButton("6h", callback_data="autobackup:set:6"),
                InlineKeyboardButton("12h", callback_data="autobackup:set:12"),
            ],
            [
                InlineKeyboardButton("Свое значение", callback_data="autobackup:custom"),
                InlineKeyboardButton("Отключить", callback_data="autobackup:off"),
            ],
            [InlineKeyboardButton("⬅️ Назад", callback_data="nav:home")],
        ]
    )


def _build_help_text(pages: List[str], page: int) -> str:
    if not pages:
        return "<b>Помощь</b>\n<blockquote>Данные помощи ещё не сгенерированы.</blockquote>"
    page = max(0, min(page, len(pages) - 1))
    header = f"<b>Помощь</b>\n<blockquote>Страница {page + 1} из {len(pages)}</blockquote>\n\n"
    return header + pages[page]


def _build_config_text(owner_id: int, log_path: str, runtime_path: str, help_path: str) -> str:
    return (
        "<b>Inline Config</b>\n"
        "<blockquote><b>Owner ID:</b> <code>{}</code></blockquote>\n"
        "<blockquote><b>Log file:</b> <code>{}</code></blockquote>\n"
        "<blockquote><b>Runtime file:</b> <code>{}</code></blockquote>\n"
        "<blockquote><b>Help file:</b> <code>{}</code></blockquote>"
    ).format(owner_id, log_path, runtime_path, help_path)


async def _run_bot(config_path: str) -> None:
    cfg = _load_config(config_path)
    owner_id = int(cfg["owner_id"])
    log_path = cfg.get("log_file", DEFAULT_LOG_FILE)
    runtime_cache = JsonCache(cfg.get("runtime_file", DEFAULT_RUNTIME_FILE), RUNTIME_CACHE_TTL)
    help_cache = JsonCache(cfg.get("help_file", DEFAULT_HELP_FILE), HELP_CACHE_TTL)
    user_config_path = f"config-{owner_id}.json"
    pending_custom: Set[int] = set()
    inline_cache: Dict[str, Tuple[float, List[InlineQueryResultArticle]]] = {}

    bot = Bot(cfg["token"], parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    def _is_owner(user_id: int) -> bool:
        return user_id == owner_id

    def _get_help_pages() -> List[str]:
        data = help_cache.read()
        pages = data.get("pages") or []
        return [str(p) for p in pages if p]

    def _runtime() -> Dict[str, Any]:
        return runtime_cache.read()

    def _load_user_config() -> Dict[str, Any]:
        if not os.path.exists(user_config_path):
            return {"prefix": "."}
        try:
            with open(user_config_path, "r", encoding="utf-8") as f:
                return json.load(f) or {"prefix": "."}
        except Exception:
            return {"prefix": "."}

    def _save_user_config(data: Dict[str, Any]) -> None:
        try:
            with open(user_config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=True)
        except Exception:
            pass

    async def _edit_message(query: CallbackQuery, text: str, markup: InlineKeyboardMarkup):
        if query.message:
            await query.message.edit_text(text, reply_markup=markup)
        else:
            await bot.send_message(query.from_user.id, text, reply_markup=markup)

    @dp.message(Command("start"))
    async def handle_start(message: Message):
        if not message.from_user or not _is_owner(message.from_user.id):
            return
        text = (
            "<b>Forelka Inline Bot</b>\n"
            "<blockquote>Используйте кнопки ниже для управления юзерботом.</blockquote>"
        )
        await message.answer(text, reply_markup=_build_home_keyboard())

    @dp.message(Command("ping"))
    async def handle_ping(message: Message):
        if not message.from_user or not _is_owner(message.from_user.id):
            return
        await message.answer(_build_ping_text(_runtime()))

    @dp.message(Command("status"))
    async def handle_status(message: Message):
        if not message.from_user or not _is_owner(message.from_user.id):
            return
        await message.answer(_build_status_text(_runtime()))

    @dp.message(Command("help"))
    async def handle_help(message: Message):
        if not message.from_user or not _is_owner(message.from_user.id):
            return
        pages = _get_help_pages()
        text = _build_help_text(pages, 0)
        await message.answer(text, reply_markup=_build_help_keyboard(0, len(pages)))

    @dp.message(Command("autobackup"))
    async def handle_autobackup(message: Message):
        if not message.from_user or not _is_owner(message.from_user.id):
            return
        cfg = _load_user_config()
        await message.answer(_build_autobackup_text(cfg), reply_markup=_build_autobackup_keyboard())

    @dp.message(Command("config"))
    async def handle_config(message: Message):
        if not message.from_user or not _is_owner(message.from_user.id):
            return
        text = _build_config_text(owner_id, log_path, runtime_cache.path, help_cache.path)
        await message.answer(text, reply_markup=_build_config_keyboard())

    @dp.message()
    async def handle_custom_hours(message: Message):
        if not message.from_user or message.from_user.id not in pending_custom:
            return
        if not _is_owner(message.from_user.id):
            return
        raw = (message.text or "").strip()
        try:
            hours = int(raw)
        except ValueError:
            await message.answer(
                "<b>Неверное значение.</b>\n<blockquote>Введите целое число часов.</blockquote>"
            )
            return
        if hours <= 0:
            await message.answer(
                "<b>Неверное значение.</b>\n<blockquote>Часы должны быть больше нуля.</blockquote>"
            )
            return
        cfg = _load_user_config()
        cfg["auto_backup_hours"] = hours
        cfg["auto_backup_next_ts"] = int(time.time() + hours * 3600)
        cfg.pop("auto_backup_disabled", None)
        _save_user_config(cfg)
        pending_custom.discard(message.from_user.id)
        await message.answer(
            f"<b>Автобекапы включены.</b>\n<blockquote>Интервал: <code>{hours}h</code></blockquote>"
        )

    @dp.callback_query()
    async def handle_callback(query: CallbackQuery):
        if not query.from_user or not _is_owner(query.from_user.id):
            await query.answer("Access denied.")
            return
        data = query.data or ""
        if data.startswith("help:close"):
            if query.message:
                try:
                    await query.message.delete()
                except Exception:
                    pass
            await query.answer()
            return
        if data.startswith("help:page:"):
            try:
                page = int(data.split(":")[-1])
            except Exception:
                page = 0
            pages = _get_help_pages()
            text = _build_help_text(pages, page)
            await _edit_message(query, text, _build_help_keyboard(page, len(pages)))
            await query.answer()
            return
        if data == "nav:status":
            await _edit_message(query, _build_status_text(_runtime()), _build_home_keyboard())
            await query.answer()
            return
        if data == "nav:home":
            await _edit_message(
                query,
                "<b>Forelka Inline Bot</b>\n<blockquote>Главное меню.</blockquote>",
                _build_home_keyboard(),
            )
            await query.answer()
            return
        if data == "nav:ping":
            await _edit_message(query, _build_ping_text(_runtime()), _build_home_keyboard())
            await query.answer()
            return
        if data == "nav:logs":
            text = _read_log_lines(log_path, 30)
            await _edit_message(
                query,
                "<b>Логи (последние 30 строк)</b>\n<blockquote expandable><code>{}</code></blockquote>".format(
                    text or "Нет данных"
                ),
                _build_home_keyboard(),
            )
            await query.answer()
            return
        if data == "nav:autobackup":
            cfg = _load_user_config()
            await _edit_message(query, _build_autobackup_text(cfg), _build_autobackup_keyboard())
            await query.answer()
            return
        if data.startswith("autobackup:set:"):
            try:
                hours = int(data.split(":")[-1])
            except Exception:
                await query.answer("Неверное значение.")
                return
            cfg = _load_user_config()
            cfg["auto_backup_hours"] = hours
            cfg["auto_backup_next_ts"] = int(time.time() + hours * 3600)
            cfg.pop("auto_backup_disabled", None)
            _save_user_config(cfg)
            await _edit_message(
                query,
                "<b>Автобекапы включены.</b>\n"
                f"<blockquote>Интервал: <code>{hours}h</code></blockquote>",
                _build_autobackup_keyboard(),
            )
            await query.answer("Готово.")
            return
        if data == "autobackup:off":
            cfg = _load_user_config()
            cfg["auto_backup_disabled"] = True
            cfg.pop("auto_backup_hours", None)
            cfg.pop("auto_backup_next_ts", None)
            _save_user_config(cfg)
            await _edit_message(
                query, "<b>Автобекапы отключены.</b>", _build_autobackup_keyboard()
            )
            await query.answer("Отключено.")
            return
        if data == "autobackup:custom":
            pending_custom.add(query.from_user.id)
            await bot.send_message(
                query.from_user.id,
                "<b>Введите своё значение в часах.</b>\n<blockquote>Пример: <code>5</code></blockquote>",
            )
            await query.answer("Ожидаю значение.")
            return
        if data == "nav:config":
            text = _build_config_text(owner_id, log_path, runtime_cache.path, help_cache.path)
            await _edit_message(query, text, _build_config_keyboard())
            await query.answer()
            return
        await query.answer()

    @dp.inline_query()
    async def inline_query_handler(inline_query: InlineQuery):
        if not inline_query.from_user or not _is_owner(inline_query.from_user.id):
            await inline_query.answer([], cache_time=1)
            return
        query = (inline_query.query or "").strip()
        cached = inline_cache.get(query)
        if cached and (time.time() - cached[0]) < INLINE_CACHE_TTL:
            await inline_query.answer(cached[1], cache_time=1)
            return

        results: List[InlineQueryResultArticle] = []
        if query == "":
            text = _read_log_lines(log_path, 20)
            results.append(
                InlineQueryResultArticle(
                    id="last_logs",
                    title="Последние 20 строк",
                    input_message_content=InputTextMessageContent(message_text=text),
                    description="Показать последние строки лога",
                    reply_markup=_build_inline_keyboard(),
                )
            )
        elif query.lower() == "status":
            text = _build_status_text(_runtime())
            results.append(
                InlineQueryResultArticle(
                    id="status",
                    title="Статус юзербота",
                    input_message_content=InputTextMessageContent(
                        message_text=text, parse_mode=ParseMode.HTML
                    ),
                    description="Проверить аптайм и обновление",
                    reply_markup=_build_inline_keyboard(),
                )
            )
        elif query.lower() == "help":
            pages = _get_help_pages()
            text = _build_help_text(pages, 0)
            results.append(
                InlineQueryResultArticle(
                    id="help",
                    title="Помощь",
                    input_message_content=InputTextMessageContent(
                        message_text=text, parse_mode=ParseMode.HTML
                    ),
                    description="Показать справку",
                    reply_markup=_build_inline_keyboard(),
                )
            )
        elif query.lower().startswith("search "):
            keyword = query[7:].strip()
            text = _search_logs(log_path, keyword, max_results=15)
            results.append(
                InlineQueryResultArticle(
                    id="search",
                    title=f"Поиск: {keyword}" if keyword else "Поиск по логам",
                    input_message_content=InputTextMessageContent(message_text=text),
                    description="Найти строку в логе",
                    reply_markup=_build_inline_keyboard(),
                )
            )
        else:
            text = (
                "Инлайн команды:\n"
                "- пустой запрос: последние строки\n"
                "- status: статус юзербота\n"
                "- help: справка\n"
                "- search <слово>: поиск по логу"
            )
            results.append(
                InlineQueryResultArticle(
                    id="usage",
                    title="Помощь по инлайну",
                    input_message_content=InputTextMessageContent(message_text=text),
                    description="Список команд",
                    reply_markup=_build_inline_keyboard(),
                )
            )

        inline_cache[query] = (time.time(), results)
        await inline_query.answer(results, cache_time=1)

    await dp.start_polling(bot)


def run_bot(config_path: str = DEFAULT_CONFIG_PATH) -> None:
    asyncio.run(_run_bot(config_path))


if __name__ == "__main__":
    run_bot()
