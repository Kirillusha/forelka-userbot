import telebot
from telebot.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
import os
import time

TOKEN = "7696280451:AAFA70tdSTfOXpdS97v8PIkcOqRhWeIvbLg"
LOG_FILE = 'forelka.log'

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
            id="last_logs",            title="📄 Последние 20 строк лога",
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