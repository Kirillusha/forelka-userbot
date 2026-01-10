import json
import os
from pyrogram.enums import ParseMode

__forelka_meta__ = {
    "lib": "system",
    "name": "Prefix",
    "version": "1.0.0",
    "developer": "forelka",
    "description": "Изменение префикса команд (сохраняется в config-*.json).",
}

async def prefix_cmd(client, message, args):
    path = f"config-{message.from_user.id}.json"
    cfg = {"prefix": "."}
    if os.path.exists(path):
        with open(path, "r") as f:
            try: cfg = json.load(f)
            except: pass

    if not args:
        current = cfg.get("prefix", ".")
        return await message.edit(f"<emoji id=5897962422169243693>👻</emoji> <b>Settings</b>\n<blockquote><b>Current prefix:</b> <code>{current}</code></blockquote>", parse_mode=ParseMode.HTML)

    new_prefix = args[0][:3]
    cfg["prefix"] = new_prefix
    with open(path, "w") as f: json.dump(cfg, f, indent=4)
    client.prefix = new_prefix
    await message.edit(f"<emoji id=5897962422169243693>👻</emoji> <b>Settings</b>\n<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Prefix set to:</b> <code>{new_prefix}</code></blockquote>", parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["prefix"] = {"func": prefix_cmd, "module": module_name, "description": "Показать/изменить префикс."}
    commands["setprefix"] = {"func": prefix_cmd, "module": module_name, "description": "Алиас команды prefix."}
