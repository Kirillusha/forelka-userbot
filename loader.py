import html
import importlib.util
import inspect
import json
import os
import sys

import requests

from pyrogram.enums import ParseMode

from meta_lib import read_module_meta

def is_protected(name):
    return os.path.exists(f"modules/{name}.py") or name in ["loader", "main"]

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

def _module_commands(app, module_name):
    cmds = [c for c, v in app.commands.items() if v.get("module") == module_name]
    cmds.sort()
    return cmds

def _format_meta_block(app, module_name):
    module = sys.modules.get(module_name)
    commands = _module_commands(app, module_name)
    meta = read_module_meta(module, module_name, commands)
    display = meta.get("name") or module_name
    version = meta.get("version") or "unknown"
    author = meta.get("author") or "unknown"
    description = meta.get("description") or ""
    location = _module_location(getattr(module, "__file__", "") if module else "")
    path = _module_path(module) or "unknown"
    pref = _get_prefix(app)

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

    cmd_list = meta.get("commands") or []
    if cmd_list:
        cmds_line = " | ".join([f"{pref}{c}" for c in cmd_list])
    else:
        cmds_line = "Нет команд"

    text = f"{info}\n\n<b>Commands:</b>\n<blockquote><code>{_escape(cmds_line)}</code></blockquote>"

    if description:
        text += f"\n\n<b>Description:</b>\n<blockquote>{_escape(description)}</blockquote>"

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

async def dlm_cmd(client, message, args):
    if len(args) < 2: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .dlm [url] [name]</b></blockquote>", parse_mode=ParseMode.HTML)
    
    url, name = args[0], args[1].lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    path = f"loaded_modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Downloading {name}...</b></blockquote>", parse_mode=ParseMode.HTML)
    
    try:
        r = requests.get(url, timeout=10)
        with open(path, "wb") as f: 
            f.write(r.content)
            
        if load_module(client, name, "loaded_modules"):
            meta_block = _format_meta_block(client, name)
            await message.edit(
                f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} installed</b></blockquote>\n\n{meta_block}",
                parse_mode=ParseMode.HTML
            )
        else: 
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: 
        await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>", parse_mode=ParseMode.HTML)

async def lm_cmd(client, message, args):
    if not message.reply_to_message or not message.reply_to_message.document:
        out = "<blockquote><b>Modules:</b>\n" + "\n".join([f" • <code>{m}</code>" for m in sorted(client.loaded_modules)]) + "</blockquote>"
        return await message.edit(out, parse_mode=ParseMode.HTML)
    
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".py"): 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>.py only</b></blockquote>", parse_mode=ParseMode.HTML)
    
    name = (args[0] if args else doc.file_name[:-3]).lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    path = f"loaded_modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5899757765743615694>⬇️</emoji> <b>Saving {name}...</b></blockquote>", parse_mode=ParseMode.HTML)
    
    try:
        await client.download_media(message.reply_to_message, file_name=path)
        if load_module(client, name, "loaded_modules"):
            meta_block = _format_meta_block(client, name)
            await message.edit(
                f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} loaded</b></blockquote>\n\n{meta_block}",
                parse_mode=ParseMode.HTML
            )
        else: 
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: 
        await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>", parse_mode=ParseMode.HTML)

async def ulm_cmd(client, message, args):
    if not args: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ulm [name]</b></blockquote>", parse_mode=ParseMode.HTML)
    
    name = args[0].lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    path = f"loaded_modules/{name}.py"
    if os.path.exists(path):
        unload_module(client, name)
        os.remove(path)
        await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} deleted</b></blockquote>", parse_mode=ParseMode.HTML)
    else: 
        await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>", parse_mode=ParseMode.HTML)

async def ml_cmd(client, message, args):
    if not args: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ml [name]</b></blockquote>", parse_mode=ParseMode.HTML)
    
    name = args[0]
    path = f"loaded_modules/{name}.py"
    if not os.path.exists(path): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>", parse_mode=ParseMode.HTML)
    
    await message.delete()
    await client.send_document(
        message.chat.id, 
        path, 
        caption=f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module:</b> <code>{name}</code></blockquote>", 
        parse_mode=ParseMode.HTML
    )

def load_module(app, name, folder):
    path = os.path.abspath(os.path.join(folder, f"{name}.py"))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        
        reg = getattr(mod, "register", None)
        if reg:
            sig = inspect.signature(reg)
            if len(sig.parameters) == 3:
                reg(app, app.commands, name)
            else:
                reg(app, app.commands)
            app.loaded_modules.add(name)
            return True
    except:
        return False
    return False

def unload_module(app, name):
    to_pop = [k for k, v in list(app.commands.items()) if v.get("module") == name]
    for k in to_pop:
        app.commands.pop(k)
    app.loaded_modules.discard(name)
    if name in sys.modules:
        del sys.modules[name]

def load_all(app):
    app.commands.update({
        "dlm": {"func": dlm_cmd, "module": "loader"},
        "lm":  {"func": lm_cmd,  "module": "loader"},
        "ulm": {"func": ulm_cmd, "module": "loader"},
        "ml":  {"func": ml_cmd,  "module": "loader"}
    })
    app.loaded_modules.add("loader")
    
    for d in ["modules", "loaded_modules"]:
        if not os.path.exists(d):
            os.makedirs(d)
        for f in sorted(os.listdir(d)):
            if f.endswith(".py") and not f.startswith("_"):
                load_module(app, f[:-3], d)
