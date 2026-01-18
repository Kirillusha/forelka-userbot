import json
import os
import time
from typing import Any, Dict, List, Optional

import telebot
from telebot.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

DEFAULT_CONFIG_PATH = os.environ.get("FORELKA_INLINE_CONFIG", "inline_bot.json")
DEFAULT_LOG_FILE = "forelka.log"
DEFAULT_RUNTIME_FILE = "runtime.json"
DEFAULT_HELP_FILE = "inline_help.json"

LOG_CACHE_TTL = 2
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
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 Статус", callback_data="nav:status"),
        InlineKeyboardButton("📶 Пинг", callback_data="nav:ping"),
    )
    keyboard.add(
        InlineKeyboardButton("📚 Помощь", callback_data="help:page:0"),
        InlineKeyboardButton("🧾 Логи", callback_data="nav:logs"),
    )
    keyboard.add(InlineKeyboardButton("🧰 Автобекапы", callback_data="nav:autobackup"))
    return keyboard


def _build_inline_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🧾 Последние строки", switch_inline_query_current_chat=""),
        InlineKeyboardButton("🔍 Поиск", switch_inline_query_current_chat="search "),
    )
    keyboard.add(
        InlineKeyboardButton("📊 Статус", switch_inline_query_current_chat="status"),
        InlineKeyboardButton("📚 Помощь", switch_inline_query_current_chat="help"),
    )
    return keyboard


def _build_help_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=3)
    nav_row: List[InlineKeyboardButton] = []
    if total_pages > 1:
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"help:page:{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f"help:page:{page + 1}"))
    if nav_row:
        keyboard.row(*nav_row)
    keyboard.add(InlineKeyboardButton("✖️ Закрыть", callback_data="help:close"))
    return keyboard


def _build_config_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔄 Обновить", callback_data="nav:config"),
        InlineKeyboardButton("📚 Помощь", callback_data="help:page:0"),
    )
    keyboard.add(InlineKeyboardButton("✖️ Закрыть", callback_data="help:close"))
    return keyboard


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
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("1h", callback_data="autobackup:set:1"),
        InlineKeyboardButton("2h", callback_data="autobackup:set:2"),
        InlineKeyboardButton("3h", callback_data="autobackup:set:3"),
    )
    keyboard.add(
        InlineKeyboardButton("4h", callback_data="autobackup:set:4"),
        InlineKeyboardButton("6h", callback_data="autobackup:set:6"),
        InlineKeyboardButton("12h", callback_data="autobackup:set:12"),
    )
    keyboard.add(
        InlineKeyboardButton("Свое значение", callback_data="autobackup:custom"),
        InlineKeyboardButton("Отключить", callback_data="autobackup:off"),
    )
    keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="nav:home"))
    return keyboard


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


def run_bot(config_path: str = DEFAULT_CONFIG_PATH) -> None:
    cfg = _load_config(config_path)
    owner_id = int(cfg["owner_id"])
    log_path = cfg.get("log_file", DEFAULT_LOG_FILE)
    runtime_cache = JsonCache(cfg.get("runtime_file", DEFAULT_RUNTIME_FILE), RUNTIME_CACHE_TTL)
    help_cache = JsonCache(cfg.get("help_file", DEFAULT_HELP_FILE), HELP_CACHE_TTL)
    user_config_path = f"config-{owner_id}.json"
    pending_custom = set()

    bot = telebot.TeleBot(cfg["token"], parse_mode="HTML")
    inline_cache: Dict[str, Any] = {}

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

    @bot.message_handler(commands=["start"])
    def handle_start(message):
        if not _is_owner(message.from_user.id):
            return
        text = (
            "<b>Forelka Inline Bot</b>\n"
            "<blockquote>Используйте кнопки ниже для управления юзерботом.</blockquote>"
        )
        bot.send_message(message.chat.id, text, reply_markup=_build_home_keyboard())

    @bot.message_handler(commands=["ping"])
    def handle_ping(message):
        if not _is_owner(message.from_user.id):
            return
        bot.send_message(message.chat.id, _build_ping_text(_runtime()))

    @bot.message_handler(commands=["status"])
    def handle_status(message):
        if not _is_owner(message.from_user.id):
            return
        bot.send_message(message.chat.id, _build_status_text(_runtime()))

    @bot.message_handler(commands=["help"])
    def handle_help(message):
        if not _is_owner(message.from_user.id):
            return
        pages = _get_help_pages()
        text = _build_help_text(pages, 0)
        bot.send_message(message.chat.id, text, reply_markup=_build_help_keyboard(0, len(pages)))

    @bot.message_handler(commands=["autobackup"])
    def handle_autobackup(message):
        if not _is_owner(message.from_user.id):
            return
        cfg = _load_user_config()
        bot.send_message(
            message.chat.id,
            _build_autobackup_text(cfg),
            reply_markup=_build_autobackup_keyboard(),
        )

    @bot.message_handler(func=lambda message: message.from_user and message.from_user.id in pending_custom)
    def handle_custom_hours(message):
        if not _is_owner(message.from_user.id):
            return
        raw = (message.text or "").strip()
        try:
            hours = int(raw)
        except ValueError:
            return bot.send_message(
                message.chat.id,
                "<b>Неверное значение.</b>\n<blockquote>Введите целое число часов.</blockquote>",
            )
        if hours <= 0:
            return bot.send_message(
                message.chat.id,
                "<b>Неверное значение.</b>\n<blockquote>Часы должны быть больше нуля.</blockquote>",
            )
        cfg = _load_user_config()
        cfg["auto_backup_hours"] = hours
        cfg["auto_backup_next_ts"] = int(time.time() + hours * 3600)
        cfg.pop("auto_backup_disabled", None)
        _save_user_config(cfg)
        pending_custom.discard(message.from_user.id)
        bot.send_message(
            message.chat.id,
            f"<b>Автобекапы включены.</b>\n<blockquote>Интервал: <code>{hours}h</code></blockquote>",
        )

    @bot.message_handler(commands=["config"])
    def handle_config(message):
        if not _is_owner(message.from_user.id):
            return
        text = _build_config_text(owner_id, log_path, runtime_cache.path, help_cache.path)
        bot.send_message(message.chat.id, text, reply_markup=_build_config_keyboard())

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        if not _is_owner(call.from_user.id):
            return bot.answer_callback_query(call.id, "Access denied.")
        data = call.data or ""
        if data.startswith("help:close"):
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            return bot.answer_callback_query(call.id)
        if data.startswith("help:page:"):
            try:
                page = int(data.split(":")[-1])
            except Exception:
                page = 0
            pages = _get_help_pages()
            text = _build_help_text(pages, page)
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_help_keyboard(page, len(pages)),
            )
            return bot.answer_callback_query(call.id)
        if data == "nav:status":
            bot.edit_message_text(
                _build_status_text(_runtime()),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_home_keyboard(),
            )
            return bot.answer_callback_query(call.id)
        if data == "nav:home":
            bot.edit_message_text(
                "<b>Forelka Inline Bot</b>\n<blockquote>Главное меню.</blockquote>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_home_keyboard(),
            )
            return bot.answer_callback_query(call.id)
        if data == "nav:ping":
            bot.edit_message_text(
                _build_ping_text(_runtime()),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_home_keyboard(),
            )
            return bot.answer_callback_query(call.id)
        if data == "nav:logs":
            text = _read_log_lines(log_path, 30)
            bot.edit_message_text(
                "<b>Логи (последние 30 строк)</b>\n<blockquote expandable><code>{}</code></blockquote>".format(
                    text or "Нет данных"
                ),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_home_keyboard(),
            )
            return bot.answer_callback_query(call.id)
        if data == "nav:autobackup":
            cfg = _load_user_config()
            bot.edit_message_text(
                _build_autobackup_text(cfg),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_autobackup_keyboard(),
            )
            return bot.answer_callback_query(call.id)
        if data.startswith("autobackup:set:"):
            try:
                hours = int(data.split(":")[-1])
            except Exception:
                return bot.answer_callback_query(call.id, "Неверное значение.")
            cfg = _load_user_config()
            cfg["auto_backup_hours"] = hours
            cfg["auto_backup_next_ts"] = int(time.time() + hours * 3600)
            cfg.pop("auto_backup_disabled", None)
            _save_user_config(cfg)
            bot.edit_message_text(
                "<b>Автобекапы включены.</b>\n"
                f"<blockquote>Интервал: <code>{hours}h</code></blockquote>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_autobackup_keyboard(),
            )
            return bot.answer_callback_query(call.id, "Готово.")
        if data == "autobackup:off":
            cfg = _load_user_config()
            cfg["auto_backup_disabled"] = True
            cfg.pop("auto_backup_hours", None)
            cfg.pop("auto_backup_next_ts", None)
            _save_user_config(cfg)
            bot.edit_message_text(
                "<b>Автобекапы отключены.</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_autobackup_keyboard(),
            )
            return bot.answer_callback_query(call.id, "Отключено.")
        if data == "autobackup:custom":
            pending_custom.add(call.from_user.id)
            bot.send_message(
                call.message.chat.id,
                "<b>Введите своё значение в часах.</b>\n"
                "<blockquote>Пример: <code>5</code></blockquote>",
            )
            return bot.answer_callback_query(call.id, "Ожидаю значение.")
        if data == "nav:config":
            text = _build_config_text(owner_id, log_path, runtime_cache.path, help_cache.path)
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=_build_config_keyboard(),
            )
            return bot.answer_callback_query(call.id)
        return bot.answer_callback_query(call.id)

    @bot.inline_handler(lambda query: True)
    def inline_query_handler(inline_query):
        if not _is_owner(inline_query.from_user.id):
            bot.answer_inline_query(inline_query.id, results=[], cache_time=1)
            return
        query = (inline_query.query or "").strip()
        cached = inline_cache.get(query)
        if cached and (time.time() - cached[0]) < INLINE_CACHE_TTL:
            bot.answer_inline_query(inline_query.id, cached[1], cache_time=1)
            return

        results = []
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
                        message_text=text, parse_mode="HTML"
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
                        message_text=text, parse_mode="HTML"
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
        bot.answer_inline_query(inline_query.id, results, cache_time=1)

    print("Inline bot is running.")
    bot.infinity_polling()


if __name__ == "__main__":
    run_bot()