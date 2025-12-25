from pyrogram.enums import ParseMode

async def username_cmd(client, message, args):
    me = await client.get_me()
    user = f"@{me.username}" if me.username else "None"
    
    res = (
        f"<emoji id=5771887475421090729>👤</emoji> <b>Account</b>\n"
        f"<blockquote><b>Username:</b> <code>{user}</code></blockquote>"
    )
    await message.edit(res, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["username"] = {"func": username_cmd, "module": module_name}
