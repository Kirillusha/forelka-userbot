import html
import json
import os
import sys
from pyrogram.enums import ParseMode

from meta_lib import read_module_meta

LIST_ALIASES = {"list", "all", "ls"}

def _escape(value):
    return html.escape(str(value)) if value is not None else ""

def _get_prefix(client):
    pref = getattr(client, "prefix", None)
    if pref:
        return pref
    path = f"config-{client.me.id}.json"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                pref = json.load(f).get("prefix", ".")
        except Exception:
            pref = "."
    return pref or "."

def _collect_commands(client):
    module_cmds = {}
    for cmd_name, info in client.commands.items():
        mod_name = info.get("module", "unknown")
        module_cmds.setdefault(mod_name, []).append(cmd_name)
    for cmds in module_cmds.values():
        cmds.sort()
    return module_cmds

def _resolve_target(target, module_names, commands_map, pref):
    cleaned = target.strip()
    if cleaned.startswith(pref):
        cleaned = cleaned[len(pref):]
    cleaned_lower = cleaned.lower()
    if cleaned_lower in commands_map:
        return commands_map[cleaned_lower]["module"], []
    exact = [m for m in module_names if m.lower() == cleaned_lower]
    if exact:
        return exact[0], []
    partial = [m for m in module_names if m.lower().startswith(cleaned_lower)]
    if len(partial) == 1:
        return partial[0], []
    return None, partial

def _render_module_detail(module_name, module, meta, pref):
    display = meta.get("name") or module_name
    version = meta.get("version") or "—"
    author = meta.get("author") or "—"
    description = meta.get("description") or ""
    commands = meta.get("commands") or []

    header = (
        f"<emoji id=5897962422169243693>👻</emoji> "
        f"<b>Forelka</b> • <b>{_escape(display)}</b>"
    )
    info = (
        "<blockquote>"
        f"<emoji id=5879770735999717115>👤</emoji> <b>Автор:</b> <code>{_escape(author)}</code>\n"
        f"<emoji id=5877396173135811032>⚙️</emoji> <b>Версия:</b> <code>{_escape(version)}</code>\n"
        f"<emoji id=5877468380125990242>➡️</emoji> <b>Команд:</b> <code>{len(commands)}</code>"
        "</blockquote>"
    )

    text = f"{header}\n\n{info}"

    if description:
        text += f"\n\n<b>Описание:</b>\n<blockquote>{_escape(description)}</blockquote>"

    if commands:
        cmds_line = " | ".join([f"{pref}{c}" for c in commands])
    else:
        cmds_line = "Нет команд"
    text += f"\n\n<b>Команды:</b>\n<blockquote expandable><code>{_escape(cmds_line)}</code></blockquote>"

    links = []
    for label, key in (("Repo", "repo"), ("Docs", "docs"), ("Source", "source")):
        value = meta.get(key)
        if value:
            links.append(f"<b>{label}:</b> <code>{_escape(value)}</code>")
    if links:
        text += "\n\n<b>Ссылки:</b>\n<blockquote>" + "\n".join(links) + "</blockquote>"

    extra = meta.get("extra") or {}
    if extra:
        extra_lines = []
        for key, value in extra.items():
            extra_lines.append(f"<b>{_escape(key)}:</b> <code>{_escape(value)}</code>")
        text += "\n\n<b>Дополнительно:</b>\n<blockquote>" + "\n".join(extra_lines) + "</blockquote>"

    return text

async def help_cmd(client, message, args):
    pref = _get_prefix(client)
    module_cmds = _collect_commands(client)
    module_names = sorted(set(module_cmds.keys()) | set(getattr(client, "loaded_modules", set())))

    if args and args[0].lower() not in LIST_ALIASES:
        target = args[0]
        module_name, matches = _resolve_target(target, module_names, client.commands, pref)
        if not module_name:
            hint = ""
            if matches:
                preview = " | ".join(sorted(matches)[:10])
                hint = f"\n<blockquote>Возможные совпадения: <code>{_escape(preview)}</code></blockquote>"
            text = (
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Модуль не найден</b></blockquote>"
                f"{hint}\n"
                f"<b>Usage:</b> <code>{_escape(pref)}help &lt;module|command&gt;</code>"
            )
            return await message.edit(text, parse_mode=ParseMode.HTML)

        module = sys.modules.get(module_name)
        meta = read_module_meta(module, module_name, module_cmds.get(module_name))
        detail = _render_module_detail(module_name, module, meta, pref)
        return await message.edit(detail, parse_mode=ParseMode.HTML)

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
    commands["help"] = {"func": help_cmd, "module": module_name}
