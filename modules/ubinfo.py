from pyrogram.types import Message

async def forelka_cmd(client, message: Message, args):
    text = (
        "💙Contacts\n\n"
        "Channel: https://t.me/forelkauserbots\n"
        "Modules: soon\n"
        "Support: https://t.me/forelusersupport"
    )
    await message.reply(text)

def register(app, commands, prefix, module_name):
    commands["ubinfo"] = {
        "func": forelka_cmd,
        "desc": "Показать информацию о Userbot Forelka",
        "module": module_name
    }
    app._commands = commands