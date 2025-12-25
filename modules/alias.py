import json
import os

def get_config(c):
    path = f"config-{c.me.id}.json"
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return {}

def save_config(c, data):
    path = f"config-{c.me.id}.json"
    with open(path, "w") as f: json.dump(data, f, indent=4)

async def alias_cmd(c, m, args):
    if len(args) < 2:
        return await m.edit("<b><emoji id=5775887550262546277>❗️</emoji> Usage: <code>.alias [short] [command]</code></b>")
    
    name, target = args[0].lower(), args[1].lower()
    config = get_config(c)
    
    if "aliases" not in config: config["aliases"] = {}
    config["aliases"][name] = target
    save_config(c, config)
    await m.edit(f"<b><emoji id=5776375003280838798>✅</emoji> Alias <code>{name}</code> -> <code>{target}</code> created</b>")

async def delalias_cmd(c, m, args):
    if not args:
        return await m.edit("<b><emoji id=5775887550262546277>❗️</emoji> Usage: <code>.delalias [name]</code></b>")
    
    name = args[0].lower()
    config = get_config(c)
    
    if "aliases" in config and name in config["aliases"]:
        del config["aliases"][name]
        save_config(c, config)
        await m.edit(f"<b><emoji id=5776375003280838798>✅</emoji> Alias <code>{name}</code> deleted</b>")
    else:
        await m.edit("<b><emoji id=5778527486270770928>❌</emoji> Alias not found</b>")

def register(app, commands, module_name):
    commands["alias"] = {"func": alias_cmd, "module": module_name}
    commands["delalias"] = {"func": delalias_cmd, "module": module_name}
