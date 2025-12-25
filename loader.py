import importlib
import importlib.util
import os
import sys
import inspect
import requests
from pyrogram.enums import ParseMode

async def dlm_cmd(client, message, args):
    if len(args) < 2:
        return await message.edit("<emoji id=5775887550262546277>❗️</emoji> <b>Usage: .dlm [url] [name]</b>", parse_mode=ParseMode.HTML)
    url, name = args[0], args[1].lower()
    if os.path.exists(f"modules/{name}.py") or name in ["loader", "main"]:
        return await message.edit("<emoji id=5778527486270770928>❌</emoji> <b>Access Denied: System module</b>", parse_mode=ParseMode.HTML)
    path = f"loaded-modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Downloading {name}...</b></blockquote>", parse_mode=ParseMode.HTML)
    try:
        r = requests.get(url, timeout=10)
        with open(path, "wb") as f:
            f.write(r.content)
        if load_module(client, name, "loaded-modules"):
            await message.edit(f"<emoji id=5776375003280838798>✅</emoji> <b>Module {name} installed to loaded-modules</b>", parse_mode=ParseMode.HTML)
        else:
            await message.edit(f"<emoji id=5778527486270770928>❌</emoji> <b>Failed to load {name}</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.edit(f"<emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code>", parse_mode=ParseMode.HTML)

async def lm_cmd(client, message, args):
    if not message.reply_to_message or not message.reply_to_message.document:
        out = "<b>Modules:</b>\n"
        for m in sorted(client.loaded_modules):
            out += f" • <code>{m}</code>\n"
        return await message.edit(out, parse_mode=ParseMode.HTML)
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".py"):
        return await message.edit("<emoji id=5775887550262546277>❗️</emoji> <b>File must be .py</b>", parse_mode=ParseMode.HTML)
    name = (args[0] if args else doc.file_name[:-3]).lower()
    if os.path.exists(f"modules/{name}.py") or name in ["loader", "main"]:
        return await message.edit("<emoji id=5778527486270770928>❌</emoji> <b>Access Denied: System module</b>", parse_mode=ParseMode.HTML)
    path = f"loaded-modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5899757765743615694>⬇️</emoji> <b>Saving {name} to loaded-modules...</b></blockquote>", parse_mode=ParseMode.HTML)
    try:
        await client.download_media(message.reply_to_message, file_name=path)
        if load_module(client, name, "loaded-modules"):
            await message.edit(f"<emoji id=5776375003280838798>✅</emoji> <b>Module {name} loaded</b>", parse_mode=ParseMode.HTML)
        else:
            await message.edit(f"<emoji id=5778527486270770928>❌</emoji> <b>Load failed</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.edit(f"<emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code>", parse_mode=ParseMode.HTML)

async def ulm_cmd(client, message, args):
    if not args:
        return await message.edit("<emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ulm [name]</b>", parse_mode=ParseMode.HTML)
    name = args[0].lower()
    if os.path.exists(f"modules/{name}.py") or name in ["loader", "main"]:
        return await message.edit("<emoji id=5778527486270770928>❌</emoji> <b>Cannot modify system folder</b>", parse_mode=ParseMode.HTML)
    path = f"loaded-modules/{name}.py"
    if os.path.exists(path):
        unload_module(client, name)
        os.remove(path)
        await message.edit(f"<emoji id=5776375003280838798>✅</emoji> <b>Module {name} deleted from loaded-modules</b>", parse_mode=ParseMode.HTML)
    else:
        await message.edit(f"<emoji id=5778527486270770928>❌</emoji> <b>Module not found in loaded-modules</b>", parse_mode=ParseMode.HTML)

async def ml_cmd(client, message, args):
    if not args:
        return await message.edit("<emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ml [name]</b>", parse_mode=ParseMode.HTML)
    name = args[0]
    file_path = f"loaded-modules/{name}.py"
    if not os.path.exists(file_path):
        return await message.edit("<emoji id=5778527486270770928>❌</emoji> <b>Module file not found in loaded-modules</b>", parse_mode=ParseMode.HTML)
    await message.delete()
    await client.send_document(message.chat.id, file_path, caption=f"<emoji id=5776375003280838798>✅</emoji> <b>Module:</b> <code>{name}</code>", parse_mode=ParseMode.HTML)

def load_module(app, name, folder):
    path = os.path.abspath(os.path.join(folder, f"{name}.py"))
    if not os.path.exists(path): return False
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None: return False
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        if hasattr(mod, "register"):
            sig = inspect.signature(mod.register)
            if len(sig.parameters) == 3: mod.register(app, app.commands, name)
            else: mod.register(app, app.commands)
            app.loaded_modules.add(name)
            return True
    except Exception as e:
        print(f"Load error {name}: {e}")
    return False

def unload_module(app, name):
    to_pop = [k for k, v in app.commands.items() if v.get("module") == name]
    for k in to_pop: app.commands.pop(k)
    app.loaded_modules.discard(name)
    if name in sys.modules: del sys.modules[name]

def load_all(app):
    app.commands["dlm"] = {"func": dlm_cmd, "module": "loader"}
    app.commands["lm"] = {"func": lm_cmd, "module": "loader"}
    app.commands["ulm"] = {"func": ulm_cmd, "module": "loader"}
    app.commands["ml"] = {"func": ml_cmd, "module": "loader"}
    app.loaded_modules.add("loader")
    for d in ["modules", "loaded-modules"]:
        if not os.path.exists(d): os.makedirs(d)
        for f in sorted(os.listdir(d)):
            if f.endswith(".py") and not f.startswith("_"): load_module(app, f[:-3], d)
