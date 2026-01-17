import json
import telebot
from telebot.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
import os
import time

LOG_FILE = 'forelka.log'

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

    return token, owner_id, config_path


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

bot = telebot.TeleBot(TOKEN)
START_TIME = time.time()
CACHE = {}
CACHE_TTL = 30

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
    return f"🟢 <b>Статус Forelka</b>\n\n🕒 Аптайм: {uptime}\n📄 Лог-файл: {'есть' if os.path.exists(LOG_FILE) else 'отсутствует'}"

def build_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📄 Последние строки", switch_inline_query_current_chat=""),
        InlineKeyboardButton("🔍 Поиск в логах", switch_inline_query_current_chat="search "),
    )
    keyboard.add(
        InlineKeyboardButton("ℹ️ Статус", switch_inline_query_current_chat="status"),
    )
    return keyboard

@bot.inline_handler(lambda query: True)
def inline_query_handler(inline_query):
    # Проверка доступа — только владелец может использовать инлайн
    if inline_query.from_user.id != OWNER_ID:
        bot.answer_inline_query(inline_query.id, results=[], cache_time=1)
        return

    query = inline_query.query.strip()

    cache_entry = CACHE.get(query)
    if cache_entry and (time.time() - cache_entry[0]) < CACHE_TTL:
        results = cache_entry[1]
        bot.answer_inline_query(inline_query.id, results, cache_time=1)
        return

    results = []

    if query == "":
        text = read_log_lines(20)
        results.append(InlineQueryResultArticle(
            id="last_logs",
            title="📄 Последние 20 строк лога",
            input_message_content=InputTextMessageContent(message_text=text),
            description="Показать последние 20 строк лога",
            reply_markup=build_keyboard()
        ))
    elif query.lower() == "status":
        text = get_status_text()
        results.append(InlineQueryResultArticle(
            id="status",
            title="ℹ️ Статус Forelka",
            input_message_content=InputTextMessageContent(message_text=text, parse_mode="HTML"),
            description="Показать статус и аптайм",
            reply_markup=build_keyboard()
        ))
    elif query.lower().startswith("search "):
        keyword = query[7:].strip()
        if not keyword:
            text = "Введите ключевое слово после команды 'search'"
        else:
            text = search_logs(keyword, max_results=15)
        results.append(InlineQueryResultArticle(
            id="search",
            title=f"🔍 Поиск: {keyword}" if keyword else "🔍 Поиск в логах",
            input_message_content=InputTextMessageContent(message_text=text),
            description=f"Результаты поиска по '{keyword}'",
            reply_markup=build_keyboard()
        ))
    else:
        text = "Используйте:\n" \
               "- Пустой запрос — последние строки лога\n" \
               "- status — статус юзербота\n" \
               "- search <слово> — поиск по логам"
        results.append(InlineQueryResultArticle(
            id="help",
            title="❓ Помощь по командам",
            input_message_content=InputTextMessageContent(message_text=text),
            description="Помощь",
            reply_markup=build_keyboard()
        ))

    CACHE[query] = (time.time(), results)
    bot.answer_inline_query(inline_query.id, results, cache_time=1)

if __name__ == "__main__":
    print("Инлайн-бот запущен...")
    bot.infinity_polling()