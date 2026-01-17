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


def _load_inline_settings():
    config_path = _find_config_file()
    cfg = {}
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    token = os.environ.get("FORELKA_INLINE_TOKEN") or cfg.get("inline_bot_token")
    owner_id = os.environ.get("FORELKA_INLINE_OWNER_ID")
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


def _load_api_credentials(owner_id):
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


TOKEN, OWNER_ID, CONFIG_PATH = _load_inline_settings()

if not TOKEN:
    raise RuntimeError(
        "Inline bot token not set. Run .inlinebot setup in userbot "
        "or set FORELKA_INLINE_TOKEN."
    )
if not OWNER_ID:
    raise RuntimeError(
        "Owner ID not set. Set FORELKA_INLINE_OWNER_ID "
        "or ensure config-<id>.json exists."
    )

API_ID, API_HASH = _load_api_credentials(OWNER_ID)

app = Client("forelka-inline", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN)
START_TIME = time.time()
CACHE = {}


def _load_config():
    if not CONFIG_PATH:
        return {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_config(cfg):
    if not CONFIG_PATH:
        return
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


def _get_modules_config(cfg):
    section = cfg.setdefault(CONFIG_SECTION, {})
    if not isinstance(section, dict):
        section = {}
        cfg[CONFIG_SECTION] = section
    return section


def _get_module_config(cfg, module_name):
    section = _get_modules_config(cfg)
    module_cfg = section.get(module_name)
    if not isinstance(module_cfg, dict):
        module_cfg = {}
        section[module_name] = module_cfg
    return module_cfg


def _set_module_config_value(module_name, key, value):
    cfg = _load_config()
    module_cfg = _get_module_config(cfg, module_name)
    module_cfg[key] = value
    _save_config(cfg)


def _delete_module_config_key(module_name, key):
    cfg = _load_config()
    section = _get_modules_config(cfg)
    module_cfg = section.get(module_name, {})
    if isinstance(module_cfg, dict) and key in module_cfg:
        module_cfg.pop(key, None)
        if not module_cfg:
            section.pop(module_name, None)
        _save_config(cfg)


def _reset_module_config(module_name):
    cfg = _load_config()
    section = _get_modules_config(cfg)
    if module_name in section:
        section.pop(module_name, None)
        _save_config(cfg)


def _list_modules():
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
    return text[:limit] + "…"


def _make_result_id(*parts):
    raw = "|".join(parts)
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:24]
    return f"forelka_{digest}"


def _format_module_config_text(module_name, module_cfg):
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


def _build_main_keyboard():
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


def _build_module_keyboard(module_name, module_cfg):
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


def read_log_lines(num_lines=20):
    if not os.path.exists(LOG_FILE):
        return "Лог-файл отсутствует."
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[-num_lines:]).strip() or "Лог пуст."


def search_logs(keyword, max_results=10):
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


def format_uptime(seconds):
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


def get_status_text():
    uptime = format_uptime(time.time() - START_TIME)
    return (
        "🟢 <b>Статус Forelka</b>\n\n"
        f"🕒 Аптайм: {uptime}\n"
        f"📄 Лог-файл: {'есть' if os.path.exists(LOG_FILE) else 'отсутствует'}"
    )


def _cfg_help_text(pref="cfg"):
    return (
        "<blockquote><emoji id=5877396173135811032>⚙️</emoji> <b>Module config</b></blockquote>\n\n"
        f"<code>{pref}</code> — список модулей\n"
        f"<code>{pref} &lt;module&gt;</code> — показать настройки\n"
        f"<code>{pref} set &lt;module&gt; &lt;key&gt; &lt;value&gt;</code> — задать значение\n"
        f"<code>{pref} del &lt;module&gt; &lt;key&gt;</code> — удалить ключ\n"
        f"<code>{pref} reset &lt;module&gt;</code> — очистить модуль"
    )


def _build_cfg_results(query):
    tokens = query.split()
    results = []
    if len(tokens) == 1 or tokens[1].lower() in {"list", "ls", "all"}:
        modules = _list_modules()
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

        cfg = _load_config()
        section = cfg.get(CONFIG_SECTION, {})
        for module_name in modules[:30]:
            module_cfg = section.get(module_name, {})
            count = len(module_cfg) if isinstance(module_cfg, dict) else 0
            text = _format_module_config_text(module_name, module_cfg if isinstance(module_cfg, dict) else {})
            markup = _build_module_keyboard(module_name, module_cfg if isinstance(module_cfg, dict) else {})
            results.append(
                InlineQueryResultArticle(
                    id=_make_result_id("cfg", module_name),
                    title=f"⚙️ {module_name}",
                    input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                    description=f"Keys: {count}",
                    reply_markup=markup,
                )
            )
        return results

    sub = tokens[1].lower()
    if sub in {"help", "?", "h"}:
        text = _cfg_help_text()
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
            text = _cfg_help_text()
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
            text = _cfg_help_text()
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
            text = _cfg_help_text()
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
            text = _cfg_help_text()
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
    cfg = _load_config()
    section = cfg.get(CONFIG_SECTION, {})
    module_cfg = section.get(module_name, {}) if isinstance(section, dict) else {}
    if not isinstance(module_cfg, dict):
        module_cfg = {}
    text = _format_module_config_text(module_name, module_cfg if isinstance(module_cfg, dict) else {})
    markup = _build_module_keyboard(module_name, module_cfg if isinstance(module_cfg, dict) else {})
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


async def _edit_inline_message(client, callback_query, text, reply_markup):
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


@app.on_inline_query()
async def inline_query_handler(client, inline_query):
    if inline_query.from_user.id != OWNER_ID:
        await inline_query.answer([], cache_time=1)
        return

    query = inline_query.query.strip()
    is_cfg = query.lower().startswith(("cfg", "config"))

    if not is_cfg:
        cache_entry = CACHE.get(query)
        if cache_entry and (time.time() - cache_entry[0]) < CACHE_TTL:
            await inline_query.answer(cache_entry[1], cache_time=1)
            return

    results = []
    lower = query.lower()

    if lower.startswith(("cfg", "config")):
        results = _build_cfg_results(query)
        await inline_query.answer(results, cache_time=0, is_personal=True)
        return

    if query == "":
        text = read_log_lines(20)
        results.append(
            InlineQueryResultArticle(
                id=_make_result_id("logs"),
                title="📄 Последние 20 строк лога",
                input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                description="Показать последние 20 строк лога",
                reply_markup=_build_main_keyboard(),
            )
        )
    elif lower == "status":
        text = get_status_text()
        results.append(
            InlineQueryResultArticle(
                id=_make_result_id("status"),
                title="ℹ️ Статус Forelka",
                input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                description="Показать статус и аптайм",
                reply_markup=_build_main_keyboard(),
            )
        )
    elif lower.startswith("search "):
        keyword = query[7:].strip()
        if not keyword:
            text = "Введите ключевое слово после команды 'search'"
        else:
            text = search_logs(keyword, max_results=15)
        results.append(
            InlineQueryResultArticle(
                id=_make_result_id("search", keyword or "empty"),
                title=f"🔍 Поиск: {keyword}" if keyword else "🔍 Поиск в логах",
                input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML),
                description=f"Результаты поиска по '{keyword}'",
                reply_markup=_build_main_keyboard(),
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
                reply_markup=_build_main_keyboard(),
            )
        )

    CACHE[query] = (time.time(), results)
    await inline_query.answer(results, cache_time=1, is_personal=True)


@app.on_chosen_inline_result()
async def chosen_inline_result_handler(client, chosen_inline_result):
    if chosen_inline_result.from_user.id != OWNER_ID:
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
            _set_module_config_value(module_name, key, parsed)
        return

    if sub in {"del", "rm", "delete"} and len(tokens) >= 4:
        module_name = tokens[2]
        key = tokens[3]
        _delete_module_config_key(module_name, key)
        return

    if sub in {"reset", "clear"} and len(tokens) >= 3:
        module_name = tokens[2]
        _reset_module_config(module_name)
        return


@app.on_callback_query()
async def callback_query_handler(client, callback_query):
    if callback_query.from_user and callback_query.from_user.id != OWNER_ID:
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

    cfg = _load_config()
    section = cfg.get(CONFIG_SECTION, {})
    module_cfg = section.get(module_name, {}) if isinstance(section, dict) else {}

    if action == "toggle" and key:
        value = module_cfg.get(key)
        if isinstance(value, bool):
            _set_module_config_value(module_name, key, not value)
        else:
            await callback_query.answer("Not a boolean value", show_alert=True)
            return
    elif action == "del" and key:
        _delete_module_config_key(module_name, key)
    elif action == "reset":
        _reset_module_config(module_name)
    elif action == "refresh":
        pass
    else:
        return

    cfg = _load_config()
    section = cfg.get(CONFIG_SECTION, {})
    module_cfg = section.get(module_name, {}) if isinstance(section, dict) else {}
    text = _format_module_config_text(module_name, module_cfg if isinstance(module_cfg, dict) else {})
    markup = _build_module_keyboard(module_name, module_cfg if isinstance(module_cfg, dict) else {})

    try:
        await _edit_inline_message(client, callback_query, text, markup)
    except Exception:
        pass
    await callback_query.answer("Updated")


if __name__ == "__main__":
    print("Инлайн-бот запущен...")
    app.run()