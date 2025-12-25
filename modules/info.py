import platform
import os

async def info_cmd(client, message, args):
    me = await client.get_me()
    owner = f"@{me.username}" if me.username else me.first_name
    
    text = (
        f"Owner: {owner}\n"
        f"OS: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}"
    )

    if os.path.exists("info.jpg"):
        await message.delete()
        await client.send_photo(message.chat.id, "info.jpg", caption=text)
    else:
        await message.edit(text)

def register(app, commands, module_name):
    commands["info"] = {"func": info_cmd, "module": module_name}
