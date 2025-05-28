from pyrogram.types import Message
from pyrogram.enums import ParseMode

async def help_cmd(client, message: Message, args):
    commands = client._commands
    prefix = client.prefix
    modules = {}
    for cmd_name, info in commands.items():
        mod = info.get("module", "unknown")
        modules.setdefault(mod, []).append(cmd_name)

    text_lines = []
    text_lines.append(f"🪐 {len(modules)} модулей доступно:\n")
    
    # Формируем построчно модули с командами в скобках
    for mod, cmds in sorted(modules.items()):
        cmds_sorted = sorted(cmds)
        cmds_str = " | ".join([f"{prefix}{cmd}" for cmd in cmds_sorted])
        text_lines.append(f"▪️ {mod}: ( {cmds_str} )")
    
    text = "\n".join(text_lines)

    try:
        await message.edit_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        await message.reply(text, parse_mode=ParseMode.HTML)

def register(app, commands, prefix, module_name):
    commands["help"] = {
        "func": help_cmd,
        "desc": "Показать это сообщение помощи",
        "module": module_name
    }
    app._commands = commands