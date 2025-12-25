import os
import requests
import loader

async def lm_cmd(client, message, args):
    if message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        name = (args[0] if args else doc.file_name[:-3]).lower()
        if loader.is_protected(name): return await message.edit("<blockquote>❌ <b>Protected</b></blockquote>")
        path = f"loaded_modules/{name}.py"
        await message.edit(f"<blockquote>⏳ <b>Installing {name}...</b></blockquote>")
        await client.download_media(message.reply_to_message, file_name=path)
        warnings, reqs = [], []
        if loader.load_module(client, name, "loaded_modules", warnings, reqs):
            m = client.meta_data.get(name, {})
            stk = "<emoji id=5877540355187937244>📤</emoji>"
            r_txt = "\n" + "\n".join([f"{stk} <code>{r}</code> installed." for r in reqs]) if reqs else ""
            res = (f"<blockquote>✅ <b>Module <code>{name}</code> installed!</b>\n\n"
                   f"<emoji id=5818865045613842183>👤</emoji> <b>Dev:</b> {m.get('developer')}\n"
                   f"{stk} <b>Ver:</b> <code>{m.get('version')}</code>\n"
                   f"<emoji id=5819077443918500243>📝</emoji> <b>Info:</b> <i>{m.get('description')}</i>{r_txt}</blockquote>")
            await message.edit(res)
        else: await message.edit("<blockquote>❌ <b>Load failed</b></blockquote>")
    else:
        mods = ", ".join([f"<code>{x}</code>" for x in sorted(client.loaded_modules)])
        await message.edit(f"<blockquote>📁 <b>Modules:</b> {mods}</blockquote>")

async def dlm_cmd(client, message, args):
    if len(args) < 2: return await message.edit("<blockquote>❗️ <b>.dlm [url] [name]</b></blockquote>")
    url, name = args[0], args[1].lower()
    if loader.is_protected(name): return await message.edit("<blockquote>❌ <b>Protected</b></blockquote>")
    path = f"loaded_modules/{name}.py"
    try:
        r = requests.get(url, timeout=10)
        with open(path, "wb") as f: f.write(r.content)
        if loader.load_module(client, name, "loaded_modules"):
            await message.edit(f"<blockquote>✅ <b><code>{name}</code> installed</b></blockquote>")
    except Exception as e: await message.edit(f"<blockquote>❌ <b>Error:</b> <code>{e}</code></blockquote>")

async def ulm_cmd(client, message, args):
    if not args: return await message.edit("<blockquote>❗️ <b>Module name required</b></blockquote>")
    name = args[0].lower()
    if loader.is_protected(name): return await message.edit("<blockquote>❌ <b>Protected</b></blockquote>")
    path = f"loaded_modules/{name}.py"
    if os.path.exists(path):
        os.remove(path)
        client.commands = {k: v for k, v in client.commands.items() if v.get("module") != name}
        client.loaded_modules.discard(name)
        await message.edit(f"<blockquote>✅ <b>Module <code>{name}</code> deleted</b></blockquote>")
    else: await message.edit("<blockquote>❌ <b>Not found</b></blockquote>")

async def ml_cmd(client, message, args):
    if not args: return await message.edit("<blockquote>❗️ <b>Module name required</b></blockquote>")
    name = args[0].lower()
    path = next((f"{f}/{name}.py" for f in ["modules", "loaded_modules"] if os.path.exists(f"{f}/{name}.py")), None)
    if not path: return await message.edit(f"<blockquote>❌ <b>Module <code>{name}</code> not found</b></blockquote>")
    topic_id = message.message_thread_id if message.message_thread_id else None
    await message.delete()
    await client.send_document(chat_id=message.chat.id, document=path, message_thread_id=topic_id)

def register(app, commands, module_name):
    commands["lm"] = {"func": lm_cmd, "module": module_name}
    commands["dlm"] = {"func": dlm_cmd, "module": module_name}
    commands["ulm"] = {"func": ulm_cmd, "module": module_name}
    commands["ml"] = {"func": ml_cmd, "module": module_name}
