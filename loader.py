import importlib.util
import os
import sys
import requests
import subprocess
import traceback

def is_protected(name):
    return name in ["loader", "main", "owners", "alias"] or os.path.exists(f"modules/{name}.py")

def check_reqs(path):
    installed = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for line in content.splitlines():
        if line.strip().startswith(("# requirements:", "# req:")):
            libs = line.split(":", 1)[1].strip().split()
            for lib in libs:
                try: 
                    subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
                    installed.append(lib)
                except: pass
    return installed

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

def load_module(app, name, folder, warnings=None, reqs_out=None):
    path = os.path.abspath(os.path.join(folder, f"{name}.py"))
    try:
        reqs = check_reqs(path)
        if reqs_out is not None: reqs_out.extend(reqs)
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

def load_all(app):
    for folder in ["modules", "loaded_modules"]:
        if not os.path.exists(folder): os.makedirs(folder)
        for file in os.listdir(folder):
            if file.endswith(".py") and file != "__init__.py":
                load_module(app, file[:-3], folder)

async def ml_cmd(client, message, args):
    if not args: return await message.edit("<blockquote>❗️ <b>Module name required</b></blockquote>")
    name = args[0].lower()
    path = next((f"{f}/{name}.py" for f in ["modules", "loaded_modules"] if os.path.exists(f"{f}/{name}.py")), None)
    if not path: return await message.edit(f"<blockquote>❌ <b>Module <code>{name}</code> not found</b></blockquote>")
    topic_id = message.message_thread_id if message.message_thread_id else None
    await message.delete()
    await client.send_document(chat_id=message.chat.id, document=path, message_thread_id=topic_id)

async def ulm_cmd(client, message, args):
    if not args: return await message.edit("<blockquote>❗️ <b>Module name required</b></blockquote>")
    name = args[0].lower()
    if is_protected(name): return await message.edit("<blockquote>❌ <b>Protected</b></blockquote>")
    path = f"loaded_modules/{name}.py"
    if os.path.exists(path):
        os.remove(path)
        client.commands = {k: v for k, v in client.commands.items() if v.get("module") != name}
        client.loaded_modules.discard(name)
        await message.edit(f"<blockquote>✅ <b>Module <code>{name}</code> deleted</b></blockquote>")
    else: await message.edit("<blockquote>❌ <b>Not found</b></blockquote>")

async def lm_cmd(client, message, args):
    if message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        name = (args[0] if args else doc.file_name[:-3]).lower()
        if is_protected(name): return await message.edit("<blockquote>❌ <b>Protected</b></blockquote>")
        path = f"loaded_modules/{name}.py"
        await message.edit(f"<blockquote>⏳ <b>Installing {name}...</b></blockquote>")
        await client.download_media(message.reply_to_message, file_name=path)
        warnings, reqs = [], []
        if load_module(client, name, "loaded_modules", warnings, reqs):
            m = client.meta_data.get(name, {})
            stk = "<emoji id=5877540355187937244>📤</emoji>"
            r_txt = "\n" + "\n".join([f"{stk} <code>{r}</code> installed." for r in reqs]) if reqs else ""
            w_txt = "\n" + "\n".join([f"{stk} <code>{w}</code> No description." for w in warnings]) if warnings else ""
            res = (f"<blockquote>✅ <b>Module <code>{name}</code> installed!</b>\n\n"
                   f"<emoji id=5818865045613842183>👤</emoji> <b>Dev:</b> {m.get('developer')}\n"
                   f"{stk} <b>Ver:</b> <code>{m.get('version')}</code>\n"
                   f"<emoji id=5819077443918500243>📝</emoji> <b>Info:</b> <i>{m.get('description')}</i>{r_txt}{w_txt}</blockquote>")
            await message.edit(res)
        else: await message.edit("<blockquote>❌ <b>Load failed</b></blockquote>")
    else:
        mods = ", ".join([f"<code>{x}</code>" for x in sorted(client.loaded_modules)])
        await message.edit(f"<blockquote>📁 <b>Modules:</b> {mods}</blockquote>")

async def dlm_cmd(client, message, args):
    if len(args) < 2: return await message.edit("<blockquote>❗️ <b>.dlm [url] [name]</b></blockquote>")
    url, name = args[0], args[1].lower()
    if is_protected(name): return await message.edit("<blockquote>❌ <b>Protected</b></blockquote>")
    path = f"loaded_modules/{name}.py"
    try:
        r = requests.get(url, timeout=10)
        with open(path, "wb") as f: f.write(r.content)
        if load_module(client, name, "loaded_modules"):
            await message.edit(f"<blockquote>✅ <b><code>{name}</code> installed</b></blockquote>")
    except Exception as e: await message.edit(f"<blockquote>❌ <b>Error:</b> <code>{e}</code></blockquote>")
