async def ubinfo_cmd(client, message, args):
    text = (
        "<emoji id=5897962422169243693>👻</emoji> <b>Forelka Userbot</b>\n\n"
        "<b>Channel:</b> @forelkauserbots\n"
        "<b>Modules:</b> @forelkausermodules\n"
        "<b>Support:</b> @forelusersupport"
    )
    await message.edit(text, disable_web_page_preview=True)

def register(app, commands, module_name):
    commands["forelka"] = {"func": ubinfo_cmd, "module": module_name}
