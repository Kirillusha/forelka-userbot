import importlib.util
import os
import sys
import inspect
import requests
import traceback
from pyrogram.enums import ParseMode

MODULE_DIRS = ["modules", "loaded_modules"]

async def dlm_cmd(client, message, args):
    if len(args) < 2:
        return await message.edit("<emoji document_id=5210952531676502223>⚠️</emoji> <b>Usage: .dlm [url] [name]</b>")
    url, name = args[0], args[1]
    path = f"loaded_modules/{name}.py"
    await message.edit(f"<blockquote><emoji document_id=5874960879434338403>🔎</emoji> <b>Downloading {name}...</b></blockquote>")
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        if load_module(client, name, "loaded_modules"):
            await message.edit(f"<emoji document_id=5451804302198711311>✅</emoji> <b>Module {name} installed!</b>")
        else:
            await message.edit(f"<emoji document_id=5210813098314704058>❌</emoji> <b>Load failed. Check console.</b>")
    except Exception as e:
        await message.edit(f"<emoji document_id=5210813098314704058>❌</emoji> <b>Error:</b> <code>{e}</code>")

async def lm_cmd(client, message, args):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.edit("<emoji document_id=5210952531676502223>⚠️</emoji> <b>Reply to a .py file!</b>")
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".py"):
        return await message.edit("<emoji document_id=5210952531676502223>⚠️</emoji> <b>Not a .py file.</b>")
    name = args[0] if args else doc.file_name[:-3]
    path = f"loaded_modules/{name}.py"
    try:
        await client.download_media(message.reply_to_message, file_name=path)
        if load_module(client, name, "loaded_modules"):
            await message.edit(f"<emoji document_id=5451804302198711311>✅</emoji> <b>Module {name} loaded!</b>")
        else:
            await message.edit(f"<emoji document_id=5210813098314704058>❌</emoji> <b>Import error. Check console.</b>")
    except Exception as e:
        await message.edit(f"<emoji document_id=5210813098314704058>❌</emoji> <b>Error:</b> <code>{e}</code>")

async def ulm_cmd(client, message, args):
    if not args:
        return await message.edit("<emoji document_id=5210952531676502223>⚠️</emoji> <b>Usage: .ulm [name]</b>")
    name, unloaded = args[0], False
    for d in MODULE_DIRS:
        path = f"{d}/{name}.py"
        if os.path.exists(path):
            unload_module(client, name)
            os.remove(path)
            unloaded = True
            break
    if unloaded:
        await message.edit(f"<emoji document_id=5451804302198711311>✅</emoji> <b>Module {name} deleted.</b>")
    else:
        await message.edit(f"<emoji document_id=5210813098314704058>❌</emoji> <b>Module not found.</b>")

async def ml_cmd(client, message, args):
    if not args:
        return await message.edit("<emoji document_id=5210952531676502223>⚠️</emoji> <b>Usage: .ml [name]</b>")
    name = args[0]
    file_path = None
    for d in MODULE_DIRS:
        path = f"{d}/{name}.py"
        if os.path.exists(path):
            file_path = path
            break
    if not file_path:
        return await message.edit("<emoji document_id=5210813098314704058>❌</emoji> <b>File not found.</b>")
    await message.delete()
    await client.send_document(message.chat.id, file_path, caption=f"<emoji document_id=5451804302198711311>✅</emoji> <b>Module:</b> <code>{name}</code>")

def load_module(app, name, folder):
    path = os.path.join(folder, f"{name}.py")
    if not os.path.exists(path): return False
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None: return False
        mod = importlib.util.module_from_spec(spec)
        if name in sys.modules: del sys.modules[name]
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        if hasattr(mod, "register"):
            sig = inspect.signature(mod.register)
            if len(sig.parameters) == 3: mod.register(app, app.commands, name)
            else: mod.register(app, app.commands)
            app.loaded_modules.add(name)
            return True
    except Exception:
        print(f"\n[!] ERROR LOADING: {name}")
        traceback.print_exc()
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
    for d in MODULE_DIRS:
        if not os.path.exists(d): os.makedirs(d)
        for f in sorted(os.listdir(d)):
            if f.endswith(".py") and not f.startswith("_"):
                load_module(app, f[:-3], d)
