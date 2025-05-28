 from pyrogram.types import Message

async def hello_command(client, message: Message, args):
    await message.reply("Привет! Я юзербот.")

def register(app, commands, prefix, module_name):
    commands["hello"] = {
        "func": hello_command,
        "desc": "Ответить приветствием.",
        "module": module_name
    }
