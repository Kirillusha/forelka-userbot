from pyrogram.types import Message

async def echo(client, message: Message, args):
    if args:
        text = " ".join(args)
    else:
        text = "Напишите текст после команды."
    
    try:
        await message.edit_text(text)
    except Exception:
        await message.reply(text)

def register(app, commands, prefix, module_name):
    commands["echo"] = {
        "func": echo,
        "desc": "Повторить сообщение",
        "module": module_name
    }