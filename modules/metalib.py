import html
import json
import os
import sys

from pyrogram.enums import ParseMode

from meta_lib import build_meta, read_module_meta


__meta__ = build_meta(
    name="Meta-Lib",
    version="1.0.0",
    author="Kirillusha",
    description="Просмотр метаданных модулей и команд.",
    commands=["meta", "metalib"],
)


LIST_ALIASES = {"list", "ls", "all"}


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
    for cmd, info in client.commands.items():
        module_name = info.get("module", "unknown")
        module_cmds.setdefault(module_name, []).append(cmd)
    for cmds in module_cmds.values():
        cmds.sort()
    return module_cmds


def _module_location(path):
    if not path:
        return "Неизвестно"
    if "loaded_modules" in path.replace("\\", "/"):
        return "Внешний"
    return "Системный"


def _module_path(module):
    path = getattr(module, "__file__", "") if module else ""
    if not path:
        return ""
    try:
        return os.path.relpath(path, os.getcwd())
    except Exception:
        return path


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


def _render_module_list(module_names, module_cmds):
    lines = []
    for name in module_names:
        module = sys.modules.get(name)
        meta = read_module_meta(module, name, module_cmds.get(name))
        display = meta.get("name") or name
        if display != name:
            display = f"{display} ({name})"
        version = meta.get("version") or "unknown"
        cmds = meta.get("commands") or []
        location = _module_location(getattr(module, "__file__", "") if module else "")
        lines.append(
            f"<emoji id=5877468380125990242>➡️</emoji> "
            f"<b>{_escape(display)}</b> <code>{_escape(version)}</code> "
            f"— <b>{len(cmds)}</b> команд • {location}"
        )
    if not lines:
        return "Нет модулей"
    return "\n".join(lines)


def _render_module_detail(module_name, module, meta, pref):
    display = meta.get("name") or module_name
    version = meta.get("version") or "unknown"
    author = meta.get("author") or "unknown"
    description = meta.get("description") or ""
    location = _module_location(getattr(module, "__file__", "") if module else "")
    path = _module_path(module) or "unknown"

    info = (
        "<blockquote>"
        f"<b>Name:</b> <code>{_escape(display)}</code>\n"
        f"<b>Module:</b> <code>{_escape(module_name)}</code>\n"
        f"<b>Version:</b> <code>{_escape(version)}</code>\n"
        f"<b>Author:</b> <code>{_escape(author)}</code>\n"
        f"<b>Location:</b> <code>{_escape(location)}</code>\n"
        f"<b>Path:</b> <code>{_escape(path)}</code>"
        "</blockquote>"
    )

    text = f"<emoji id=5897962422169243693>👻</emoji> <b>Meta-Lib</b>\n\n{info}"

    if description:
        text += f"\n\n<b>Description:</b>\n<blockquote>{_escape(description)}</blockquote>"

    commands = meta.get("commands") or []
    if commands:
        cmds_line = " | ".join([f"{pref}{c}" for c in commands])
    else:
        cmds_line = "Нет команд"
    text += f"\n\n<b>Commands:</b>\n<blockquote><code>{_escape(cmds_line)}</code></blockquote>"

    links = []
    for label, key in (("Repo", "repo"), ("Docs", "docs"), ("Source", "source")):
        value = meta.get(key)
        if value:
            links.append(f"<b>{label}:</b> <code>{_escape(value)}</code>")
    if links:
        text += "\n\n<b>Links:</b>\n<blockquote>" + "\n".join(links) + "</blockquote>"

    extra = meta.get("extra") or {}
    if extra:
        extra_lines = []
        for key, value in extra.items():
            extra_lines.append(f"<b>{_escape(key)}:</b> <code>{_escape(value)}</code>")
        text += "\n\n<b>Extra:</b>\n<blockquote>" + "\n".join(extra_lines) + "</blockquote>"

    return text


async def meta_cmd(client, message, args):
    pref = _get_prefix(client)
    module_cmds = _collect_commands(client)
    module_names = sorted(set(module_cmds.keys()) | set(getattr(client, "loaded_modules", set())))

    if not args or args[0].lower() in LIST_ALIASES:
        body = _render_module_list(module_names, module_cmds)
        text = (
            "<emoji id=5897962422169243693>👻</emoji> <b>Meta-Lib</b>\n\n"
            f"<b>Modules:</b>\n<blockquote expandable>{body}</blockquote>\n\n"
            "<b>Usage:</b>\n"
            f"<code>{_escape(pref)}meta &lt;module|command&gt;</code>\n"
            f"<code>{_escape(pref)}meta list</code>"
        )
        return await message.edit(text, parse_mode=ParseMode.HTML)

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
            f"<b>Usage:</b> <code>{_escape(pref)}meta &lt;module|command&gt;</code>"
        )
        return await message.edit(text, parse_mode=ParseMode.HTML)

    module = sys.modules.get(module_name)
    meta = read_module_meta(module, module_name, module_cmds.get(module_name))
    detail = _render_module_detail(module_name, module, meta, pref)
    await message.edit(detail, parse_mode=ParseMode.HTML)


def register(app, commands, module_name):
    commands["meta"] = {"func": meta_cmd, "module": module_name}
    commands["metalib"] = {"func": meta_cmd, "module": module_name}
