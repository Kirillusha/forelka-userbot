import json
import os

def get_config(c):
    path = f"config-{c.me.id}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"prefix": ".", "aliases": {}}

def save_config(c, data):
    path = f"config-{c.me.id}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

async def alias_cmd(c, m, args):
    config = get_config(c)
    aliases = config.get("aliases", {})

    if not args:
        if not aliases:
            return await m.edit("<b><emoji id=5778527486270770928>❌</emoji> No aliases found</b>")
        
        out = "<b><emoji id=5877468380125990242>➡️</emoji> Active Aliases:</b>\n"
        for a, t in aliases.items():
            out += f"<blockquote><code>{a}</code> -> <code>{t}</code></blockquote>"
        return await m.edit(out)

    if len(args) == 1:
        name = args[0].lower()
        if name in aliases:
            del aliases[name]
            config["aliases"] = aliases
            save_config(c, config)
            return await m.edit(f"<b><emoji id=5776375003280838798>✅</emoji> Alias <code>{name}</code> deleted</b>")
        return await m.edit("<b><emoji id=5775887550262546277>❗️</emoji> Use: <code>.alias [name] [target]</code></b>")

    name, target = args[0].lower(), args[1].lower()
    aliases[name] = target
    config["aliases"] = aliases
    save_config(c, config)
    await m.edit(f"<b><emoji id=5776375003280838798>✅</emoji> Alias <code>{name}</code> -> <code>{target}</code></b>")

def register(app, commands, module_name):
    commands["alias"] = {"func": alias_cmd, "module": module_name}
