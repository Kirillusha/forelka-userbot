import time
from pyrogram.types import Message

async def ping(client, message: Message, args):
    start = time.perf_counter()  # время начала
    try:
        # Сначала редакция сообщения в "Pong!"
        await message.edit_text("Pong!")
        end = time.perf_counter()  # время после редактирования
        latency_ms = (end - start) * 1000
        # Отредактируем сообщение еще раз, чтобы добавить задержку
        await message.edit_text(f"Pong! 🏓\nЗадержка: {latency_ms:.2f} ms")
    except Exception:
        # Если не получилось отредактировать сообщение, отправим новое
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        await message.reply(f"Pong! 🏓\nЗадержка: {latency_ms:.2f} ms")

def register(app, commands, prefix, module_name):
    commands["ping"] = {
        "func": ping,
        "desc": "Проверить отклик",
        "module": module_name
    }