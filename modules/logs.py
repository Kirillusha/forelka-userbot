import os

async def log_cmd(client, message, args):
    log_file = "forelka.log"
    if os.path.exists(log_file):
        await client.send_document("me", log_file, caption="Logs")
        await message.edit("Logs sent to Saved Messages")
    else:
        await message.edit("Log file not found")

def register(app, commands, module_name):
    commands["log"] = {"func": log_cmd, "module": module_name}
