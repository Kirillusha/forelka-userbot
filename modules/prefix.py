async def prefix_cmd(client, message, args):
    if not args:
        return await message.edit(f"Current prefix: {client.prefix}")
    
    new_prefix = args[0][:3]
    client.prefix = new_prefix
    
    if hasattr(client, "db"):
        client.db.set("prefix", new_prefix)
        
    await message.edit(f"Prefix set to: {new_prefix}")

def register(app, commands, module_name):
    commands["prefix"] = {"func": prefix_cmd, "module": module_name}
