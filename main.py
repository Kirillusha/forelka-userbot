import asyncio
import os
import sys
from pyrogram import Client, idle, filters, utils
from pyrogram.handlers import MessageHandler
import loader

def print_banner(commit):
    print("  __               _ _         ")
    print(" / _|             | | |        ")
    print("| |_ ___  _ __ ___| | | ____ _ ")
    print("|  _/ _ \\| '__/ _ \\ | |/ / _` |")
    print("| || (_) | | |  __/ |   < (_| |")
    print("|_| \\___/|_|  \\___|_|_|\\_\\__,_|")
    print("                               ")
    print("Forelka Started")
    print(f"Git: #{commit}")
    print()

def get_git_commit():
    import subprocess
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except:
        return "unknown"

def patch_pyrogram():
    real_get_peer_type = utils.get_peer_type
    def get_peer_type_patched(peer_id: int) -> str:
        try:
            return real_get_peer_type(peer_id)
        except ValueError:
            if str(peer_id).startswith("-100"):
                return "channel"
            return "chat"
    utils.get_peer_type = get_peer_type_patched

async def dispatch_command(client, message):
    if not message.text or not message.text.startswith("."):
        return
    
    parts = message.text.split(maxsplit=1)
    cmd_name = parts[0][1:].lower()
    args = parts[1].split() if len(parts) > 1 else []
    
    if cmd_name in client.commands:
        try:
            await client.commands[cmd_name]["func"](client, message, args)
        except Exception as e:
            print(f"Error in {cmd_name}: {e}")
            await message.edit(f"**Error:** `{e}`")

async def main():
    patch_pyrogram()
    
    session = next((f[:-8] for f in os.listdir() if f.startswith("forelka-") and f.endswith(".session")), None)
    if not session:
        print("Session not found. Please implement auth or place session file.")
        return
    
    client = Client(session)
    client.commands = {}
    client.loaded_modules = set()
    
    client.add_handler(MessageHandler(dispatch_command, filters.me & filters.text))
    
    loader.load_all_modules(client)
    
    print_banner(get_git_commit())
    await client.start()
    await idle()
    await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
