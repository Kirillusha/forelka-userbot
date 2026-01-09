async def ubinfo_cmd(client, message, args):
    text = (
        "Forelka Userbot\n\n"
        "Channel: @forelkauserbots\n"
        "Modules: @forelkausermodules\n"
        "Support: @forelka_support"
    )
    await message.edit(text, disable_web_page_preview=True)

def register(app, commands, module_name):
    commands["forelka"] = {"func": ubinfo_cmd, "module": module_name}
