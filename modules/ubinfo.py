from pyrogram.types import Message
from pyrogram.enums import ParseMode

async def forelka_cmd(client, message: Message, args):
    text = (
        "💙Userbot Forelka started!\n\n"
        "Channel: https://t.me/forelkauserbots\n"
        "Modules: soon\n"
        "Support: https://t.me/forelusersupport"
    )
    try:
        await message.edit_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        # Если редактирование не удалось (например, сообщение не от бота), отправим ответ
        await message.reply(text)

def register(app, commands, prefix, module_name):
    commands["forelka"] = {
        "func": forelka_cmd,
        "desc": "Показать информацию о Userbot Forelka",
        "module": module_name
    }
    app._commands = commands
