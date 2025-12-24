from pyrogram.enums import ParseMode

async def help_cmd(client, message, args):
    prefix = getattr(client, "prefix", ".")
    modules = {}
    for cmd_name, info in client.commands.items():
        mod = info.get("module", "unknown")
        modules.setdefault(mod, []).append(cmd_name)

    content = ""
    for mod, cmds in sorted(modules.items()):
        cmds_str = " | ".join([f"{prefix}{c}" for c in sorted(cmds)])
        content += f"<emoji id=5877468380125990242>➡️</emoji> <b>{mod}</b>\n<code>{cmds_str}</code>\n\n"

    text = (
        f"<emoji id=5897962422169243693>👻</emoji> <b>Forelka Modules</b>\n"
        f"<blockquote>{content.strip()}</blockquote>"
    )
    await message.edit(text, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["help"] = {"func": help_cmd, "module": module_name}
