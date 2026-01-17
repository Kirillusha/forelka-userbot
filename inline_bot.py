import asyncio
import hashlib
import html
import json
import os
import re
import time

try:
    from kurigram import Client
    from kurigram.enums import ParseMode
    from kurigram.types import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        InlineQueryResultArticle,
        InputTextMessageContent,
    )
except ImportError:
    from pyrogram import Client
    from pyrogram.enums import ParseMode
    from pyrogram.types import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        InlineQueryResultArticle,
        InputTextMessageContent,
    )

LOG_FILE = "forelka.log"
CACHE_TTL = 30
CONFIG_SECTION = "modules_config"
CALLBACK_SAFE_RE = re.compile(r"^[0-9A-Za-z_.-]{1,32}$")
MODULES_MENU_LIMIT = 36
INLINE_CLIENT_NAME = "forelka-inline"

_inline_service = None


def _find_config_file():
    explicit = os.environ.get("FORELKA_CONFIG", "").strip()
    if explicit and os.path.exists(explicit):
        return explicit
    candidates = [f for f in os.listdir() if f.startswith("config-") and f.endswith(".json")]
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p))
    return candidates[-1]


def _owner_id_from_config_path(path):
    if not path:
        return None
    try:
        base = os.path.splitext(os.path.basename(path))[0]
        return int(base.split("-", 1)[1])
    except Exception:
        return None


def load_inline_settings(override_owner_id=None, override_token=None):
    config_path = _find_config_file()
    cfg = {}
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    token = override_token or os.environ.get("FORELKA_INLINE_TOKEN") or cfg.get("inline_bot_token")

    owner_id = override_owner_id or os.environ.get("FORELKA_INLINE_OWNER_ID")
    if owner_id:
        try:
            owner_id = int(owner_id)
        except Exception:
            owner_id = None
    if not owner_id:
        owner_id = _owner_id_from_config_path(config_path)
    if not owner_id:
        owners = cfg.get("owners")
        if isinstance(owners, list) and owners:
            try:
                owner_id = int(owners[0])
            except Exception:
                owner_id = None

    if not config_path and owner_id:
        config_path = f"config-{owner_id}.json"

    return token, owner_id, config_path


def load_api_credentials(owner_id):
    api_id = os.environ.get("FORELKA_API_ID")
    api_hash = os.environ.get("FORELKA_API_HASH")
    if api_id and api_hash:
        return int(api_id), str(api_hash)

    if owner_id:
        path = f"telegram_api-{owner_id}.json"
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return int(data["api_id"]), str(data["api_hash"])
            except Exception:
                pass

    raise RuntimeError(
        "API ID/HASH not found. Set FORELKA_API_ID/FORELKA_API_HASH "
        "or create telegram_api-<id>.json."
    )


def _parse_value(raw):
    text = str(raw).strip()
    if not text:
        return ""
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]
    lower = text.lower()
    if lower in {"true", "on", "yes"}:
        return True
    if lower in {"false", "off", "no"}:
        return False
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        try:
            return float(text)
        except Exception:
            return text
    return text


def _stringify_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _truncate(text, limit=3800):
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _make_result_id(*parts):
    raw = "|".join(parts)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:24]
    return f"forelka_{digest}"


def _is_callback_safe(value):
    return bool(CALLBACK_SAFE_RE.fullmatch(value or ""))


def _make_callback_data(action, module_name, key=None):
    if not _is_callback_safe(module_name):
        return None
    if key and not _is_callback_safe(key):
        return None
    parts = ["cfg", action, module_name]
    if key:
        parts.append(key)
    data = "|".join(parts)
    if len(data) > 60:
        return None
    return data


class InlineBotService:
    def __init__(self, token, owner_id, config_path, api_id, api_hash):
        self.token = token
        self.owner_id = owner_id
        self.config_path = config_path
        self.app = Client(INLINE_CLIENT_NAME, api_id=api_id, api_hash=api_hash, bot_token=token)
        self.start_time = time.time()
        self.cache = {}
        self.cache_ttl = CACHE_TTL
        self._register_handlers()

    def _register_handlers(self):
        self.app.on_inline_query()(self._inline_query_handler)
        self.app.on_chosen_inline_result()(self._chosen_inline_result_handler)
        self.app.on_callback_query()(self._callback_query_handler)

    def is_running(self):
        return bool(getattr(self.app, "is_connected", False))

    async def start(self):
        await self.app.start()

    async def stop(self):
        await self.app.stop()

    def _load_config(self):
        if not self.config_path:
            return {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_config(self, cfg):
        if not self.config_path:
            return
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)

    def _get_modules_config(self, cfg):
        section = cfg.setdefault(CONFIG_SECTION, {})
        if not isinstance(section, dict):
            section = {}
            cfg[CONFIG_SECTION] = section
        return section

    def _get_module_config(self, cfg, module_name):
        section = self._get_modules_config(cfg)
        module_cfg = section.get(module_name)
        if not isinstance(module_cfg, dict):
            module_cfg = {}
            section[module_name] = module_cfg
        return module_cfg

    def _set_module_config_value(self, module_name, key, value):
        cfg = self._load_config()
        module_cfg = self._get_module_config(cfg, module_name)
        module_cfg[key] = value
        self._save_config(cfg)

    def _delete_module_config_key(self, module_name, key):
        cfg = self._load_config()
        section = self._get_modules_config(cfg)
        module_cfg = section.get(module_name, {})
        if isinstance(module_cfg, dict) and key in module_cfg:
            module_cfg.pop(key, None)
            if not module_cfg:
                section.pop(module_name, None)
            self._save_config(cfg)

    def _reset_module_config(self, module_name):
        cfg = self._load_config()
        section = self._get_modules_config(cfg)
        if module_name in section:
            section.pop(module_name, None)
            self._save_config(cfg)

    def _list_modules(self):
        modules = set()
        for folder in ("modules", "loaded_modules"):
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                if not name.endswith(".py"):
                    continue
                if name.startswith("_") or name == "__init__.py":
                    continue
                modules.add(name[:-3])
        return sorted(modules)

    def _format_module_config_text(self, module_name, module_cfg):
        title = (
            "<blockquote>"
            "<emoji id=5877396173135811032>⚙️</emoji> "
            f"<b>Module config:</b> <code>{html.escape(module_name)}</code>"
            "</blockquote>"
        )
        if module_cfg:
            lines = []
            for key in sorted(module_cfg.keys()):
                value = module_cfg.get(key)
                line = f"{key} = {_stringify_value(value)}"
                lines.append(line)
            body = f"<blockquote expandable><code>{html.escape(chr(10).join(lines))}</code></blockquote>"
        else:
            body = "<blockquote><code>Нет настроек</code></blockquote>"

        hint = (
            "<b>Usage:</b> <code>cfg set &lt;module&gt; &lt;key&gt; &lt;value&gt;</code>\n"
            "<b>Delete:</b> <code>cfg del &lt;module&gt; &lt;key&gt;</code>"
        )
        return _truncate(f"{title}\n\n{body}\n\n{hint}")

    def _cfg_menu_text(self, modules):
        count = len(modules)
        return (
            "<blockquote><emoji id=5877396173135811032>⚙️</emoji> <b>Module config</b></blockquote>\n\n"
            f"<b>Модулей:</b> <code>{count}</code>\n"
            "<b>Выберите модуль кнопкой ниже</b>\n\n"
            "<b>Usage:</b> <code>cfg &lt;module&gt;</code>\n"
            "<b>Search:</b> <code>cfg set &lt;module&gt; &lt;key&gt; &lt;value&gt;</code>"
        )

    def _build_modules_menu_keyboard(self, modules):
        rows = []
        row = []
        for module_name in modules[:MODULES_MENU_LIMIT]:
            row.append(
                InlineKeyboardButton(
                    f"⚙️ {module_name}",
                    switch_inline_query_current_chat=f"cfg {module_name}",
                )
            )
            if len(row) >= 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("➕ Add key", switch_inline_query_current_chat="cfg set ")])
        if len(modules) > MODULES_MENU_LIMIT:
            rows.append([InlineKeyboardButton("🔍 Search module", switch_inline_query_current_chat="cfg ")])
        return InlineKeyboardMarkup(rows)

    def _build_main_keyboard(self):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📄 Последние строки", switch_inline_query_current_chat=""),
                    InlineKeyboardButton("🔍 Поиск в логах", switch_inline_query_current_chat="search "),
                ],
                [
                    InlineKeyboardButton("ℹ️ Статус", switch_inline_query_current_chat="status"),
                    InlineKeyboardButton("⚙️ Config", switch_inline_query_current_chat="cfg "),
                ],
            ]
        )

    def _build_module_keyboard(self, module_name, module_cfg):
        rows = []
        for key in sorted(module_cfg.keys()):
            value = module_cfg.get(key)
            toggle_cb = _make_callback_data("toggle", module_name, key) if isinstance(value, bool) else None
            delete_cb = _make_callback_data("del", module_name, key)
            edit_query = f"cfg set {module_name} {key} "

            if toggle_cb and delete_cb:
                rows.append(
                    [
                        InlineKeyboardButton(f"🔁 {key}", callback_data=toggle_cb),
                        InlineKeyboardButton(f"🗑 {key}", callback_data=delete_cb),
                    ]
                )
            elif delete_cb:
                rows.append(
                    [
                        InlineKeyboardButton(f"✏️ {key}", switch_inline_query_current_chat=edit_query),
                        InlineKeyboardButton(f"🗑 {key}", callback_data=delete_cb),
                    ]
                )
            else:
                rows.append(
                    [InlineKeyboardButton(f"✏️ {key}", switch_inline_query_current_chat=edit_query)]
                )

        rows.append([InlineKeyboardButton("➕ Add key", switch_inline_query_current_chat=f"cfg set {module_name} ")])
        reset_cb = _make_callback_data("reset", module_name)
        if reset_cb and module_cfg:
            rows.append([InlineKeyboardButton("🧹 Reset module", callback_data=reset_cb)])
        refresh_cb = _make_callback_data("refresh", module_name)
        if refresh_cb:
            rows.append([InlineKeyboardButton("🔄 Refresh", callback_data=refresh_cb)])

        return InlineKeyboardMarkup(rows) if rows else None

    def read_log_lines(self, num_lines=20):
        if not os.path.exists(LOG_FILE):
            return "Лог-файл отсутствует."
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-num_lines:]).strip() or "Лог пуст."

    def search_logs(self, keyword, max_results=10):
        if not os.path.exists(LOG_FILE):
            return "Лог-файл отсутствует."
        keyword = keyword.lower()
        found = []
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if keyword in line.lower():
                    found.append(line.strip())
                    if len(found) >= max_results:
                        break
        if not found:
            return f"По запросу '{keyword}' ничего не найдено."
        return "\n".join(found)

    def _format_uptime(self, seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        parts = []
        if d > 0:
            parts.append(f"{int(d)}д")
        if h > 0:
            parts.append(f"{int(h)}ч")
        if m > 0:
            parts.append(f"{int(m)}м")
        parts.append(f"{int(s)}с")
        return " ".join(parts)

    def get_status_text(self):
        uptime = self._format_uptime(time.time() - self.start_time)
        return (
            "🟢 <b>Статус Forelka</b>\n\n"
            f"🕒 Аптайм: {uptime}\n"
            f"📄 Лог-файл: {'есть' if os.path.exists(LOG_FILE) else 'отсутствует'}"
        )

    def _cfg_help_text(self, pref="cfg"):
        return (
            "<blockquote><emoji id=5877396173135811032>⚙️</emoji> <b>Module config</b></blockquote>\n\n"
            f"<code>{pref}</code> — список модулей\n"
            f"<code>{pref} &lt;module&gt;</code> — показать настройки\n"
            f"<code>{pref} set &lt;module&gt; &lt;key&gt; &lt;value&gt;</code> — задать значение\n"
            f"<code>{pref} del &lt;module&gt; &lt;key&gt;</code> — удалить ключ\n"
            f"<code>{pref} reset &lt;module&gt;</code> — очистить модуль"
        )

    def _build_cfg_results(self, query):
        tokens = query.split()
        results = []
        if len(tokens) == 1 or tokens[1].lower() in {"list", "ls", "all"}:
            modules = self._list_modules()
            if not modules:
                text = "<blockquote><b>Modules not found</b></blockquote>"
                results.append(
                    InlineQueryResultArticle(
                        id=_make_result_id("cfg", "empty"),
                        title="⚙️ Module config",
                        input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                        description="No modules found",
                    )
                )
                return results

            text = self._cfg_menu_text(modules)
            markup = self._build_modules_menu_keyboard(modules)
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("cfg", "menu"),
                    title="⚙️ Module config",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description="Выберите модуль кнопкой",
                    reply_markup=markup,
                )
            )
            return results

        sub = tokens[1].lower()
        if sub in {"help", "?", "h"}:
            text = self._cfg_help_text()
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("cfg", "help"),
                    title="⚙️ Module config help",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description="Usage",
                )
            )
            return results

        if sub in {"set", "add", "put"}:
            if len(tokens) < 4:
                text = self._cfg_help_text()
                results.append(
                    InlineQueryResultArticle(
                        id=_make_result_id("cfg", "set", "help"),
                        title="⚙️ Module config",
                        input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                        description="Set requires module/key/value",
                    )
                )
                return results
            module_name = tokens[2]
            key = tokens[3]
            value = " ".join(tokens[4:]).strip()
            if not value:
                text = self._cfg_help_text()
                results.append(
                    InlineQueryResultArticle(
                        id=_make_result_id("cfg", "set", "noval"),
                        title="⚙️ Module config",
                        input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                        description="Value is required",
                    )
                )
                return results
            parsed = _parse_value(value)
            text = (
                "<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Config updated</b></blockquote>\n\n"
                f"<b>Module:</b> <code>{html.escape(module_name)}</code>\n"
                f"<b>Key:</b> <code>{html.escape(key)}</code>\n"
                f"<b>Value:</b> <code>{html.escape(_stringify_value(parsed))}</code>"
            )
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("cfg", "set", module_name, key),
                    title=f"✅ Set {module_name}.{key}",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description=str(parsed),
                )
            )
            return results

        if sub in {"del", "rm", "delete"}:
            if len(tokens) < 4:
                text = self._cfg_help_text()
                results.append(
                    InlineQueryResultArticle(
                        id=_make_result_id("cfg", "del", "help"),
                        title="⚙️ Module config",
                        input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                        description="Delete requires module/key",
                    )
                )
                return results
            module_name = tokens[2]
            key = tokens[3]
            text = (
                "<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Key deleted</b></blockquote>\n\n"
                f"<b>Module:</b> <code>{html.escape(module_name)}</code>\n"
                f"<b>Key:</b> <code>{html.escape(key)}</code>"
            )
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("cfg", "del", module_name, key),
                    title=f"🗑 Delete {module_name}.{key}",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description="Remove key",
                )
            )
            return results

        if sub in {"reset", "clear"}:
            if len(tokens) < 3:
                text = self._cfg_help_text()
                results.append(
                    InlineQueryResultArticle(
                        id=_make_result_id("cfg", "reset", "help"),
                        title="⚙️ Module config",
                        input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                        description="Reset requires module",
                    )
                )
                return results
            module_name = tokens[2]
            text = (
                "<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module config reset</b></blockquote>\n\n"
                f"<b>Module:</b> <code>{html.escape(module_name)}</code>"
            )
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("cfg", "reset", module_name),
                    title=f"🧹 Reset {module_name}",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description="Remove all keys",
                )
            )
            return results

        module_name = tokens[1]
        cfg = self._load_config()
        section = cfg.get(CONFIG_SECTION, {})
        module_cfg = section.get(module_name, {}) if isinstance(section, dict) else {}
        if not isinstance(module_cfg, dict):
            module_cfg = {}
        text = self._format_module_config_text(module_name, module_cfg)
        markup = self._build_module_keyboard(module_name, module_cfg)
        results.append(
            InlineQueryResultArticle(
                id=_make_result_id("cfg", module_name, "detail"),
                title=f"⚙️ {module_name}",
                input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                description="Module settings",
                reply_markup=markup,
            )
        )
        return results

    async def _edit_inline_message(self, client, callback_query, text, reply_markup):
        text = _truncate(text)
        if callback_query.message:
            await callback_query.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
            return
        if callback_query.inline_message_id:
            await client.edit_inline_text(
                callback_query.inline_message_id,
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )

    async def _inline_query_handler(self, client, inline_query):
        if inline_query.from_user.id != self.owner_id:
            await inline_query.answer([], cache_time=1)
            return

        query = inline_query.query.strip()
        is_cfg = query.lower().startswith(("cfg", "config"))

        if not is_cfg:
            cache_entry = self.cache.get(query)
            if cache_entry and (time.time() - cache_entry[0]) < self.cache_ttl:
                await inline_query.answer(cache_entry[1], cache_time=1)
                return

        results = []
        lower = query.lower()

        if lower.startswith(("cfg", "config")):
            results = self._build_cfg_results(query)
            await inline_query.answer(results, cache_time=0, is_personal=True)
            return

        if query == "":
            text = self.read_log_lines(20)
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("logs"),
                    title="📄 Последние 20 строк лога",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description="Показать последние 20 строк лога",
                    reply_markup=self._build_main_keyboard(),
                )
            )
        elif lower == "status":
            text = self.get_status_text()
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("status"),
                    title="ℹ️ Статус Forelka",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description="Показать статус и аптайм",
                    reply_markup=self._build_main_keyboard(),
                )
            )
        elif lower.startswith("search "):
            keyword = query[7:].strip()
            if not keyword:
                text = "Введите ключевое слово после команды 'search'"
            else:
                text = self.search_logs(keyword, max_results=15)
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("search", keyword or "empty"),
                    title=f"🔍 Поиск: {keyword}" if keyword else "🔍 Поиск в логах",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description=f"Результаты поиска по '{keyword}'",
                    reply_markup=self._build_main_keyboard(),
                )
            )
        else:
            text = (
                "Используйте:\n"
                "- Пустой запрос — последние строки лога\n"
                "- status — статус юзербота\n"
                "- search <слово> — поиск по логам\n"
                "- cfg — настройки модулей"
            )
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("help"),
                    title="❓ Помощь по командам",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description="Помощь",
                    reply_markup=self._build_main_keyboard(),
                )
            )

        self.cache[query] = (time.time(), results)
        await inline_query.answer(results, cache_time=1, is_personal=True)

    async def _chosen_inline_result_handler(self, client, chosen_inline_result):
        if chosen_inline_result.from_user.id != self.owner_id:
            return
        query = chosen_inline_result.query.strip()
        tokens = query.split()
        if not tokens:
            return
        if tokens[0].lower() not in {"cfg", "config"}:
            return
        if len(tokens) < 2:
            return
        sub = tokens[1].lower()

        if sub in {"set", "add", "put"} and len(tokens) >= 4:
            module_name = tokens[2]
            key = tokens[3]
            value = " ".join(tokens[4:]).strip()
            if value:
                parsed = _parse_value(value)
                self._set_module_config_value(module_name, key, parsed)
            return

        if sub in {"del", "rm", "delete"} and len(tokens) >= 4:
            module_name = tokens[2]
            key = tokens[3]
            self._delete_module_config_key(module_name, key)
            return

        if sub in {"reset", "clear"} and len(tokens) >= 3:
            module_name = tokens[2]
            self._reset_module_config(module_name)
            return

    async def _callback_query_handler(self, client, callback_query):
        if callback_query.from_user and callback_query.from_user.id != self.owner_id:
            await callback_query.answer("Access denied", show_alert=True)
            return
        data = callback_query.data or ""
        if not data.startswith("cfg|"):
            return

        parts = data.split("|")
        if len(parts) < 3:
            return

        action = parts[1]
        module_name = parts[2]
        key = parts[3] if len(parts) > 3 else None

        cfg = self._load_config()
        section = cfg.get(CONFIG_SECTION, {})
        module_cfg = section.get(module_name, {}) if isinstance(section, dict) else {}
        if not isinstance(module_cfg, dict):
            module_cfg = {}

        if action == "toggle" and key:
            value = module_cfg.get(key)
            if isinstance(value, bool):
                self._set_module_config_value(module_name, key, not value)
            else:
                await callback_query.answer("Not a boolean value", show_alert=True)
                return
        elif action == "del" and key:
            self._delete_module_config_key(module_name, key)
        elif action == "reset":
            self._reset_module_config(module_name)
        elif action == "refresh":
            pass
        else:
            return

        cfg = self._load_config()
        section = cfg.get(CONFIG_SECTION, {})
        module_cfg = section.get(module_name, {}) if isinstance(section, dict) else {}
        if not isinstance(module_cfg, dict):
            module_cfg = {}
        text = self._format_module_config_text(module_name, module_cfg)
        markup = self._build_module_keyboard(module_name, module_cfg)

        try:
            await self._edit_inline_message(client, callback_query, text, markup)
        except Exception:
            pass
        await callback_query.answer("Updated")


def get_inline_bot_service():
    return _inline_service


async def ensure_inline_bot(owner_id=None, token=None, restart=False):
    global _inline_service

    if _inline_service and _inline_service.is_running():
        if not restart:
            return _inline_service, "already running"
        try:
            await _inline_service.stop()
        except Exception:
            pass
        _inline_service = None

    resolved_token, resolved_owner_id, config_path = load_inline_settings(
        override_owner_id=owner_id,
        override_token=token,
    )
    if not resolved_token:
        return None, "missing token"
    if not resolved_owner_id:
        return None, "missing owner id"

    try:
        api_id, api_hash = load_api_credentials(resolved_owner_id)
    except Exception as e:
        return None, str(e)

    service = InlineBotService(resolved_token, resolved_owner_id, config_path, api_id, api_hash)
    await service.start()
    _inline_service = service
    return service, "started"


async def stop_inline_bot():
    global _inline_service
    if not _inline_service:
        return
    try:
        await _inline_service.stop()
    finally:
        _inline_service = None


async def run_standalone():
    service, status = await ensure_inline_bot()
    if not service:
        raise RuntimeError(f"Inline bot not started: {status}")
    print("Инлайн-бот запущен...")
    try:
        try:
            from kurigram import idle
        except ImportError:
            from pyrogram import idle
        await idle()
    finally:
        await stop_inline_bot()


if __name__ == "__main__":
    asyncio.run(run_standalone())
