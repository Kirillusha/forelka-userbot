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

def get_meta(path):
    meta = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("# "):
                line = line.replace("# ", "", 1).strip()
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip().lower()] = val.strip()
    return meta

async def lm_cmd(client, message, args):
    if message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        if not doc.file_name.endswith(".py"): 
            return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>.py only</b></blockquote>")

        name = (args[0] if args else doc.file_name[:-3]).lower()
        if is_protected(name): 
            return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>")

        path = f"loaded_modules/{name}.py"
        await message.edit(f"<blockquote><emoji id=5899757765743615694>⬇️</emoji> <b>Saving {name}...</b></blockquote>")
        
        await client.download_media(message.reply_to_message, file_name=path)
        
        warnings = []
        if load_module(client, name, "loaded_modules", warnings): 
            warn_text = "\n".join([f"⚠️ <code>{w}</code> No description." for w in warnings])
            msg = f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} loaded</b>\n{warn_text}</blockquote>"
            await message.edit(msg)
        else: 
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>")
    else:
        out = "<blockquote><b>Modules:</b>\n" + "\n".join([f" • <code>{m}</code>" for m in sorted(client.loaded_modules)]) + "</blockquote>"
        await message.edit(out)

async def dlm_cmd(client, message, args):
    if len(args) < 2: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>.dlm [url] [name]</b></blockquote>")

    url, name = args[0], args[1].lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>")

    path = f"loaded_modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5891211339170326418>⏳</emoji> <b>Downloading {name}...</b></blockquote>")

    try:
        r = requests.get(url, timeout=10)
        with open(path, "wb") as f: f.write(r.content)
        
        warnings = []
        if load_module(client, name, "loaded_modules", warnings):
            warn_text = "\n".join([f"⚠️ <code>{w}</code> No description." for w in warnings])
            msg = f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} installed</b>\n{warn_text}</blockquote>"
            await message.edit(msg)
        else: 
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>")
    except Exception as e: 
        await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>")

async def ulm_cmd(client, message, args):
    if not args: return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>.ulm [name]</b></blockquote>")
    name = args[0].lower()
    if is_protected(name): return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>")
    path = f"loaded_modules/{name}.py"
    if os.path.exists(path):
        unload_module(client, name)
        os.remove(path)
        await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} deleted</b></blockquote>")
    else: 
        await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>")

async def ml_cmd(client, message, args):
    if not args: return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>.ml [name]</b></blockquote>")
    name = args[0]
    p1, p2 = f"modules/{name}.py", f"loaded_modules/{name}.py"
    final_path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
    if not final_path: return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>")
    await message.delete()
    await client.send_document(message.chat.id, final_path, caption=f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module:</b> <code>{name}</code></blockquote>")

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
            if not hasattr(app, "meta"): app.meta = {}
            app.meta[name] = get_meta(path)
            app.loaded_modules.add(name)
            return True
    except: print(traceback.format_exc())
    return False

def unload_module(app, name):
    to_pop = [k for k, v in list(app.commands.items()) if v.get("module") == name]
    for k in to_pop: app.commands.pop(k)
    app.loaded_modules.discard(name)

def load_all(app):
    app.commands.update({
        "dlm": {"func": dlm_cmd, "module": "loader"},
        "lm":  {"func": lm_cmd,  "module": "loader"},
        "ulm": {"func": ulm_cmd, "module": "loader"},
        "ml":  {"func": ml_cmd,  "module": "loader"}
    })
    for d in ["modules", "loaded_modules"]:
        if not os.path.exists(d): os.makedirs(d)
        for f in sorted(os.listdir(d)):
            if f.endswith(".py") and not f.startswith("_"): load_module(app, f[:-3], d)
