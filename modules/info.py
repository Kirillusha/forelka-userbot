import platform
import os
from pyrogram.types import Message
from pyrogram import Client

VERSION = "1.0.0 (beta)"
IMAGE_PATH = "info.jpg"  # путь к изображению

# Для демонстрации — словарь с ID по user_id, лучше сохранить в базу или файл
user_message_ids = {}

async def info(client: Client, message: Message, args):
    me = await client.get_me()
    # Получаем имя владельца: username если есть, иначе имя и фамилия
    if me.username:
        owner_name = f"@{me.username}"
    else:
        owner_name = f"{me.first_name} {me.last_name or ''}".strip()

    device_name = platform.node()
    os_name = platform.system()
    os_version = platform.release()

    info_text = (
        "💙FORELKA Userbot💙\n\n"
        f"🧑‍💻 Владелец: {owner_name}\n"
        f"📱 Устройство: {device_name}\n"
        f"🖥️ Платформа: {os_name} {os_version}\n"
        f"🚀 Версия бота: {VERSION}"
    )

    chat_id = message.chat.id
    user_id = message.from_user.id

    try:
        if user_id in user_message_ids:
            msg_id = user_message_ids[user_id]
            # Редактируем подпись у существующего сообщения с фото
            await client.edit_message_caption(chat_id, msg_id, caption=info_text)
        else:
            if os.path.exists(IMAGE_PATH):
                sent_msg = await message.reply_photo(photo=IMAGE_PATH, caption=info_text)
                # Сохраняем ID этого сообщения, чтобы редактировать позже
                user_message_ids[user_id] = sent_msg.message_id
            else:
                # Если нет фото — просто редактируем исходное сообщение
                await message.edit(info_text)
    except Exception as e:
        print(f"Ошибка: {e}")

def register(app, commands, prefix, module_name):
    commands["info"] = {
        "func": info,
        "desc": "Показать информацию о боте с фото и редактировать подпись",
        "module": module_name
    }