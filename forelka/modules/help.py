# name: Help
# version: 1.0.0
# developer: forelka
# description: Список команд и модулей (system/external).

import sys
from pyrogram.enums import ParseMode

async def help_cmd(client, message, args):
    pref = getattr(client, "prefix", ".")
    sys_mods, ext_mods = {}, {}

    for cmd_name, info in client.commands.items():
        mod_name = info.get("module", "unknown")
        mod_path = getattr(sys.modules.get(mod_name), "__file__", "")
        target = ext_mods if "loaded_modules" in mod_path else sys_mods
        target.setdefault(mod_name, []).append(cmd_name)

    def format_mods(mods_dict):
        res = ""
        for mod, cmds in sorted(mods_dict.items()):
            cmds_str = " | ".join([f"{pref}{c}" for c in sorted(cmds)])
            res += f"<emoji id=5877468380125990242>➡️</emoji> <b>{mod}</b> (<code>{cmds_str}</code>)\n"
        return res.strip()

    text = f"<emoji id=5897962422169243693>👻</emoji> <b>Forelka Modules</b>\n\n"
    if sys_mods:
        text += f"<b>System:</b>\n<blockquote expandable>{format_mods(sys_mods)}</blockquote>\n\n"
    if ext_mods:
        text += f"<b>External:</b>\n<blockquote expandable>{format_mods(ext_mods)}</blockquote>"
    else:
        text += f"<b>External:</b>\n<blockquote>No external modules</blockquote>"

    await message.edit(text, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["help"] = {"func": help_cmd, "module": module_name, "description": "Список модулей и команд."}
