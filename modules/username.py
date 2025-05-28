from pyrogram.types import Message
from pyrogram.enums import ParseMode

async def username_cmd(client, message: Message, args):
    # Получаем информацию о текущем пользователе
    me = await client.get_me()
    
    # Формируем текст с юзернеймом
    if me.username:
        text = f"🧑‍💻 Ваш юзернейм: @{me.username}"
    else:
        text = "🧑‍💻 У вас нет установленного юзернейма."
    
    try:
        await message.edit_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        await message.reply(text, parse_mode=ParseMode.HTML)

def register(app, commands, prefix, module_name):
    commands["username"] = {
        "func": username_cmd,
        "desc": "Показать ваш юзернейм аккаунта",
        "module": module_name
    }
    app._commands = commands