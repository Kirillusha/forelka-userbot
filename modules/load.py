import os
import requests
from forelka import loader

async def lm_cmd(client, message, args):
    if message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        name = doc.file_name[:-3].lower()
        
        if loader.is_protected(name): 
            return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Module is protected</b></blockquote>")
        
        path = f"loaded_modules/{name}.py"
        await message.edit(f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Installing <code>{name}</code>...</b></blockquote>")
        
        await client.download_media(message.reply_to_message, file_name=path)
        warnings, reqs = [], []
        
        if loader.load_module(client, name, "loaded_modules", warnings, reqs):
            m = client.meta_data.get(name, {})
            stk = "<emoji id=5877468380125990242>➡️</emoji>"
            r_txt = "\n" + "\n".join([f"{stk} <code>{r}</code> installed" for r in reqs]) if reqs else ""
            
            res = (f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module <code>{name}</code> installed!</b>\n\n"
                   f"<emoji id=5771887475421090729>👤</emoji> <b>Dev:</b> {m.get('developer')}\n"
                   f"{stk} <b>Ver:</b> <code>{m.get('version')}</code>\n"
                   f"<emoji id=5775887550262546277>❗️</emoji> <b>Info:</b> <i>{m.get('description')}</i>{r_txt}</blockquote>")
            await message.edit(res)
        else: 
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>")
    else:
        mods = ", ".join([f"<code>{x}</code>" for x in sorted(client.loaded_modules)])
        await message.edit(f"<blockquote><emoji id=5877468380125990242>➡️</emoji> <b>Loaded modules:</b>\n\n{mods}</blockquote>")

async def dlm_cmd(client, message, args):
    if len(args) < 2: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: <code>.dlm [url] [name]</code></b></blockquote>")
    
    url, name = args[0], args[1].lower()
    if loader.is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Module is protected</b></blockquote>")
    
    path = f"loaded_modules/{name}.py"
    try:
        await message.edit(f"<blockquote><emoji id=5899757765743615694>⬇️</emoji> <b>Downloading...</b></blockquote>")
        r = requests.get(url, timeout=10)
        with open(path, "wb") as f: 
            f.write(r.content)
            
        if loader.load_module(client, name, "loaded_modules"):
            await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b><code>{name}</code> installed via URL</b></blockquote>")
        else:
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Failed to load module</b></blockquote>")
    except Exception as e: 
        await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>")

async def ulm_cmd(client, message, args):
    if not args: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Module name required</b></blockquote>")
    
    name = args[0].lower()
    if loader.is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Module is protected</b></blockquote>")
    
    path = f"loaded_modules/{name}.py"
    if os.path.exists(path):
        os.remove(path)
        client.commands = {k: v for k, v in client.commands.items() if v.get("module") != name}
        client.loaded_modules.discard(name)
        await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module <code>{name}</code> deleted</b></blockquote>")
    else: 
        await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Module not found</b></blockquote>")

async def ml_cmd(client, message, args):
    if not args: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Module name required</b></blockquote>")
    
    name = args[0].lower()
    path = None
    for folder in ["modules", "loaded_modules"]:
        full_path = f"{folder}/{name}.py"
        if os.path.exists(full_path):
            path = full_path
            break
    
    if not path: 
        return await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Module <code>{name}</code> not found</b></blockquote>")
    
    file_name = os.path.basename(path)
    topic_id = message.message_thread_id if message.message_thread_id else None
    
    await message.delete()
    await client.send_document(
        chat_id=message.chat.id, 
        document=path, 
        caption=f"<blockquote><emoji id=5877468380125990242>➡️</emoji> <b>File:</b> <code>{file_name}</code></blockquote>",
        message_thread_id=topic_id
    )

def register(app, commands, module_name):
    commands["lm"] = {"func": lm_cmd, "module": module_name}
    commands["dlm"] = {"func": dlm_cmd, "module": module_name}
    commands["ulm"] = {"func": ulm_cmd, "module": module_name}
    commands["ml"] = {"func": ml_cmd, "module": module_name}
