import os
import datetime
from pyrogram import Client
from pyrogram.types import Message

LOG_DIR = "logs"
OWNER_ID = 5941415177  # замените на ваш ID Telegram (число)

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def get_log_filename():
    # Логи будут с датой и временем в имени
    now = datetime.datetime.now()
    return os.path.join(LOG_DIR, f"log_{now.strftime('%Y-%m-%d_%H-%M-%S')}.txt")

def write_log(text: str):
    """
    Добавляет запись в текущий дневной лог.
    Можно улучшить и создавать файлы по дате, а не по времени.
    """
    log_file = os.path.join(LOG_DIR, f"log_{datetime.datetime.now().strftime('%Y-%m-%d')}.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"[{timestamp}] {text}\n")

async def send_logs(client: Client, message: Message):
    """
    Отправка всех логов владельцу или в указанный чат.
    """
    try:
        files_sent = 0
        for filename in sorted(os.listdir(LOG_DIR)):
            filepath = os.path.join(LOG_DIR, filename)
            if os.path.isfile(filepath):
                await client.send_document(
                    OWNER_ID,
                    filepath,
                    caption=f"Лог файл: {filename}"
                )
                files_sent += 1
        
        if files_sent == 0:
            await message.reply("Логов пока нет.")
        else:
            await message.reply(f"Отправлено {files_sent} файлов логов.")
    except Exception as e:
        await message.reply(f"Ошибка при отправке логов: {e}")

async def log_command(client: Client, message: Message, args):
    """
    Команда /log — для отправки логов владельцу
    """
    # Тут можно проверить, что команду запускает владелец
    if message.from_user and message.from_user.id == OWNER_ID:
        await send_logs(client, message)
    else:
        await message.reply("У вас нет доступа к команде.")

def register(app, commands, prefix, module_name):
    commands["log"] = {
        "func": log_command,
        "desc": "Отправить все файлы логов владельцу",
        "module": module_name
    }