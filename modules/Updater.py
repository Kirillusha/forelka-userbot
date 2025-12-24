import os
import sys
import subprocess

async def update_cmd(client, message, args):
    await message.edit("Updating...")
    try:
        res = subprocess.check_output(["git", "pull"]).decode()
        if "Already up to date" in res:
            return await message.edit("Already up to date")
        
        await message.edit("Restarting...")
        os.execv(sys.executable, [sys.executable, "main.py"])
    except Exception as e:
        await message.edit(f"Error: {e}")

async def restart_cmd(client, message, args):
    await message.edit("Restarting...")
    os.execv(sys.executable, [sys.executable, "main.py"])

def register(app, commands, module_name):
    commands["update"] = {"func": update_cmd, "module": module_name}
    commands["restart"] = {"func": restart_cmd, "module": module_name}
