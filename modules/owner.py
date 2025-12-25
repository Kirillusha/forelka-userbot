import json
import os

def get_config(c):
    path = f"config-{c.me.id}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"prefix": ".", "owners": [], "aliases": {}}

def save_config(c, data):
    path = f"config-{c.me.id}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

async def owner_cmd(c, m, args):
    config = get_config(c)
    owners = config.get("owners", [])

    if not args and not m.reply_to_message:
        if not owners:
            return await m.edit("<b><emoji id=5778527486270770928>❌</emoji> Owners list is empty</b>")
        
        out = "<b><emoji id=5771887475421090729>👤</emoji> Authorized Owners:</b>\n"
        for o in owners:
            out += f"<blockquote><code>{o}</code></blockquote>"
        return await m.edit(out)

    user_id = None
    if m.reply_to_message:
        user_id = m.reply_to_message.from_user.id
    else:
        try:
            user_id = int(args[0])
        except (ValueError, IndexError):
            return await m.edit("<b><emoji id=5775887550262546277>❗️</emoji> Provide a valid ID or reply</b>")

    if user_id == c.me.id:
        return await m.edit("<b><emoji id=5775887550262546277>❗️</emoji> You are the main owner</b>")

    if user_id not in owners:
        owners.append(user_id)
        config["owners"] = owners
        save_config(c, config)
        await m.edit(f"<b><emoji id=5776375003280838798>✅</emoji> Added <code>{user_id}</code> to owners</b>")
    else:
        owners.remove(user_id)
        config["owners"] = owners
        save_config(c, config)
        await m.edit(f"<b><emoji id=5776375003280838798>✅</emoji> Removed <code>{user_id}</code> from owners</b>")

def register(app, commands, module_name):
    commands["owner"] = {"func": owner_cmd, "module": module_name}
