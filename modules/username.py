async def username_cmd(client, message, args):
    me = await client.get_me()
    res = f"Username: @{me.username}" if me.username else "No username set"
    await message.edit(res)

def register(app, commands, module_name):
    commands["username"] = {"func": username_cmd, "module": module_name}
