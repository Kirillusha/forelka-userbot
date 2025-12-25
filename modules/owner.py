import json
import os

def get_config(c):
    path = f"config-{c.me.id}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_config(c, data):
    path = f"config-{c.me.id}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

async def add_owner(c, m, args):
    user_id = None
    if m.reply_to_message:
        user_id = m.reply_to_message.from_user.id
    elif args:
        try:
            user_id = int(args[0])
        except ValueError:
            return await m.edit("<b><emoji id=5775887550262546277>❗️</emoji> Provide a valid ID</b>")
    
    if not user_id:
        return await m.edit("<b><emoji id=5891243564309942507>💬</emoji> Reply to a user or provide an ID</b>")
    
    config = get_config(c)
    owners = config.get("owners", [])
    
    if user_id not in owners:
        owners.append(user_id)
        config["owners"] = owners
        save_config(c, config)
        await m.edit(f"<b><emoji id=5776375003280838798>✅</emoji> User <code>{user_id}</code> added to owners</b>")
    else:
        await m.edit("<b><emoji id=5775887550262546277>❗️</emoji> Already an owner</b>")

async def del_owner(c, m, args):
    user_id = None
    if m.reply_to_message:
        user_id = m.reply_to_message.from_user.id
    elif args:
        try: user_id = int(args[0])
        except: pass
            
    config = get_config(c)
    owners = config.get("owners", [])
    
    if user_id in owners:
        owners.remove(user_id)
        config["owners"] = owners
        save_config(c, config)
        await m.edit(f"<b><emoji id=5776375003280838798>✅</emoji> User <code>{user_id}</code> removed from owners</b>")
    else:
        await m.edit("<b><emoji id=5778527486270770928>❌</emoji> Owner not found</b>")

def register(app, commands, module_name):
    commands["owner"] = {"func": add_owner, "module": module_name}
    commands["delowner"] = {"func": del_owner, "module": module_name}
