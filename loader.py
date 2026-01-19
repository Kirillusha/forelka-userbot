import html
import importlib.util
import inspect
import json
import os
import sys

import requests

from pyrogram.enums import ParseMode

from meta_lib import extract_command_descriptions, read_module_meta

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

def _module_commands(app, module_name):
    cmds = [c for c, v in app.commands.items() if v.get("module") == module_name]
    cmds.sort()
    return cmds

def _first_line(text):
    if not text:
        return ""
    return str(text).strip().splitlines()[0].strip()

def _command_descriptions(app, module_name, commands):
    module = sys.modules.get(module_name)
    raw_meta = getattr(module, "__meta__", None) if module else None
    meta_descs = extract_command_descriptions(raw_meta)
    result = {}
    for cmd in commands:
        key = cmd.lower()
        desc = ""
        info = app.commands.get(cmd, {})
        if isinstance(info, dict):
            desc = info.get("description") or info.get("desc") or info.get("about") or info.get("help") or ""
        desc = _first_line(desc)
        if not desc:
            desc = meta_descs.get(key, "")
        if not desc:
            func = app.commands.get(cmd, {}).get("func")
            desc = _first_line(getattr(func, "__doc__", ""))
        result[key] = desc
    return result

def _format_meta_block(app, module_name):
    module = sys.modules.get(module_name)
    commands = _module_commands(app, module_name)
    meta = read_module_meta(module, module_name, commands)
    display = meta.get("name") or module_name
    author = meta.get("author") or "Не указан"
    description = _first_line(meta.get("description")) or "Нет описания"
    pref = _get_prefix(app)

    cmd_descs = _command_descriptions(app, module_name, commands)
    if commands:
        lines = []
        for cmd in commands:
            desc = cmd_descs.get(cmd.lower()) or "нет описания"
            lines.append(f"{_escape(pref + cmd)} — {_escape(desc)}")
        cmds_block = "\n".join(lines)
    else:
        cmds_block = _escape("Нет команд")

    loaded_line = (
        "<blockquote>"
        f"<emoji id=5776375003280838798>✅</emoji> "
        f"<b>Модуль</b> <code>{_escape(display)}</code> <b>загружен</b>"
        "</blockquote>"
    )
    desc_line = (
        "<blockquote>"
        f"<emoji id=5877396173135811032>⚙️</emoji> "
        f"<b>Описание:</b> {_escape(description)}"
        "</blockquote>"
    )
    commands_block = f"<blockquote expandable><code>{cmds_block}</code></blockquote>"
    author_line = (
        "<blockquote>"
        f"<emoji id=5879770735999717115>👤</emoji> "
        f"<b>Разработчик:</b> <code>{_escape(author)}</code>"
        "</blockquote>"
    )

    return f"{loaded_line}\n{desc_line}\n\n{commands_block}\n\n{author_line}"

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
            await message.edit(meta_block, parse_mode=ParseMode.HTML)
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
            await message.edit(meta_block, parse_mode=ParseMode.HTML)
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
                
