async def help_cmd(client, message, args):
    prefix = getattr(client, "prefix", ".")
    modules = {}
    
    for cmd_name, info in client.commands.items():
        mod = info.get("module", "unknown")
        modules.setdefault(mod, []).append(cmd_name)

    text = [f"Modules: {len(modules)}\n"]
    for mod, cmds in sorted(modules.items()):
        cmds_str = " | ".join([f"{prefix}{c}" for c in sorted(cmds)])
        text.append(f"{mod}: ( {cmds_str} )")

    await message.edit("\n".join(text))

def register(app, commands, module_name):
    commands["help"] = {"func": help_cmd, "module": module_name}
