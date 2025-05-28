from pyrogram.types import Message

async def change_prefix(client, message: Message, args):
    db = client.db
    if not args:
        text = (f"Текущий префикс: `{client.prefix}`\n"
                f"Чтобы изменить, напишите: {client.prefix}prefix <новый_префикс>")
        try:
            await message.edit_text(text)
        except Exception:
            await message.reply(text)
        return

    new_prefix = args[0]
    if len(new_prefix) > 3:
        text = "Префикс слишком длинный, максимум 3 символа."
        try:
            await message.edit_text(text)
        except Exception:
            await message.reply(text)
        return

    client.prefix = new_prefix
    db.set("prefix", new_prefix)
    text = f"Префикс команд изменён на: `{new_prefix}`"
    try:
        await message.edit_text(text)
    except Exception:
        await message.reply(text)

def register(app, commands, prefix, module_name):
    commands["prefix"] = {
        "func": change_prefix,
        "desc": "Показать или изменить префикс команд. Использование: prefix <новый_префикс>",
        "module": module_name
    }