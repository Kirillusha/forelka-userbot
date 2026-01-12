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
            mod_title = getattr(client, "module_title", lambda x: x)(mod)
            cmds_str = " | ".join([f"{pref}{c}" for c in sorted(cmds)])
            line = getattr(client, "t", lambda k, default=None, **kw: default or k)(
                "help.module_line",
                default="<emoji id=5877468380125990242>➡️</emoji> <b>{module}</b> (<code>{cmds}</code>)",
                module=mod_title,
                cmds=cmds_str,
            )
            res += f"{line}\n"
        return res.strip()

    t = getattr(client, "t", lambda k, default=None, **kw: default or k)
    text = f"<emoji id=5897962422169243693>👻</emoji> <b>{t('help.title', default='Forelka Modules')}</b>\n\n"
    if sys_mods:
        text += f"<b>{t('help.section_system', default='System:')}</b>\n<blockquote expandable>{format_mods(sys_mods)}</blockquote>\n\n"
    if ext_mods:
        text += f"<b>{t('help.section_external', default='External:')}</b>\n<blockquote expandable>{format_mods(ext_mods)}</blockquote>"
    else:
        text += f"<b>{t('help.section_external', default='External:')}</b>\n<blockquote>{t('help.no_external', default='No external modules')}</blockquote>"

    await message.edit(text, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["help"] = {"func": help_cmd, "module": module_name}
