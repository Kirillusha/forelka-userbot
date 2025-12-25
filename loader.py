import importlib.util
import os
import sys
import inspect
import requests
import subprocess
import traceback
from pyrogram.enums import ParseMode

def is_protected(name):
    return name in ["loader", "main", "owners", "alias"] or os.path.exists(f"modules/{name}.py")

def check_reqs(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for line in content.splitlines():
        if line.strip().startswith(("# requirements:", "# req:")):
            libs = line.split(":", 1)[1].strip().split()
            for lib in libs:
                subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

def get_full_meta(path):
    meta = {"developer": "Unknown", "description": "No description provided.", "version": "1.0"}
    if not os.path.exists(path): return meta
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("# meta"):
                parts = line.replace("# meta", "").strip().split(":", 1)
                if len(parts) == 2:
                    meta[parts[0].strip().lower()] = parts[1].strip()
    return meta

def load_module(app, name, folder, warnings=None):
    path = os.path.abspath(os.path.join(folder, f"{name}.py"))
    try:
        check_reqs(path)
        if name in sys.modules: del sys.modules[name]
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        reg = getattr(mod, "register", None)
        if reg:
            temp_commands = {}
            reg(app, temp_commands, name)
            for cmd_name, cmd_data in temp_commands.items():
                func = cmd_data.get("func")
                if warnings is not None and (not func.__doc__ or not func.__doc__.strip()):
                    warnings.append(cmd_name)
                app.commands[cmd_name] = cmd_data
            if not hasattr(app, "meta_data"): app.meta_data = {}
            app.meta_data[name] = get_full_meta(path)
            app.loaded_modules.add(name)
            return True
    except: print(traceback.format_exc())
    return False

async def lm_cmd(client, message, args):
    if message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        name = (args[0] if args else doc.file_name[:-3]).lower()
        if is_protected(name): 
            return await message.edit("<blockquote><emoji id=5210952531676504517>❌</emoji> <b>Access Denied</b></blockquote>")
        
        path = f"loaded_modules/{name}.py"
        await message.edit(f"<blockquote><emoji id=5891211339170326418>⏳</emoji> <b>Installing {name}...</b></blockquote>")
        await client.download_media(message.reply_to_message, file_name=path)
        
        warnings = []
        if load_module(client, name, "loaded_modules", warnings):
            m = client.meta_data.get(name, {})
            warn = "\n" + "\n".join([f"<emoji id=5443001153207968501>⚠️</emoji> <code>{w}</code> No description." for w in warnings]) if warnings else ""
            res = (
                f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module <code>{name}</code> installed!</b>\n\n"
                f"<emoji id=5818865045613842183>👤</emoji> <b>Dev:</b> {m.get('developer')}\n"
                f"<emoji id=5260216654721195614>📦</emoji> <b>Ver:</b> <code>{m.get('version')}</code>\n"
                f"<emoji id=5819077443918500243>📝</emoji> <b>Info:</b> <i>{m.get('description')}</i>{warn}</blockquote>"
            )
            await message.edit(res)
        else: await message.edit("<blockquote><emoji id=5210952531676504517>❌</emoji> <b>Load failed</b></blockquote>")
    else:
        out = "<blockquote><emoji id=5258380200344819745>📁</emoji> <b>Loaded Modules:</b>\n" + "\n".join([f" <emoji id=5258410226343743510>•</emoji> <code>{m}</code>" for m in sorted(client.loaded_modules)]) + "</blockquote>"
        await message.edit(out)

async def dlm_cmd(client, message, args):
    if len(args) < 2: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>.dlm [url] [name]</b></blockquote>")
    url, name = args[0], args[1].lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5210952531676504517>❌</emoji> <b>Access Denied</b></blockquote>")
    
    path = f"loaded_modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5891211339170326418>⏳</emoji> <b>Downloading {name}...</b></blockquote>")
    try:
        r = requests.get(url, timeout=10)
        with open(path, "wb") as f: f.write(r.content)
        warnings = []
        if load_module(client, name, "loaded_modules", warnings):
            m = client.meta_data.get(name, {})
            warn = "\n" + "\n".join([f"<emoji id=5443001153207968501>⚠️</emoji> <code>{w}</code> No description." for w in warnings]) if warnings else ""
            res = (
                f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module <code>{name}</code> installed!</b>\n\n"
                f"<emoji id=5818865045613842183>👤</emoji> <b>Dev:</b> {m.get('developer')}\n"
                f"<emoji id=5260216654721195614>📦</emoji> <b>Ver:</b> <code>{m.get('version')}</code>\n"
                f"<emoji id=5819077443918500243>📝</emoji> <b>Info:</b> <i>{m.get('description')}</i>{warn}</blockquote>"
            )
            await message.edit(res)
        else: await message.edit("<blockquote><emoji id=5210952531676504517>❌</emoji> <b>Load failed</b></blockquote>")
    except Exception as e: 
        await message.edit(f"<blockquote><emoji id=5210952531676504517>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>")