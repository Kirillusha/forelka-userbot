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

def find_session():
    for f in os.listdir():
        if f.startswith("forelka-") and f.endswith(".session"):
            return f[:-8]
    return None

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

async def hikka_like_auth():
    api_id = int(input("API ID: ").strip())
    api_hash = input("API Hash: ").strip()
    phone = input("Phone: ").strip()
    client = Client("temp_auth", api_id=api_id, api_hash=api_hash)
    await client.start()
    me = await client.get_me()
    name = f"forelka-{me.id}"
    await client.stop()
    if os.path.exists(f"{name}.session"):
        os.remove(f"{name}.session")
    os.rename("temp_auth.session", f"{name}.session")
    return Client(name, api_id=api_id, api_hash=api_hash)

async def dispatch_command(client, message):
    if not message.text or not message.text.startswith("."):
        return
    
    parts = message.text.split(maxsplit=1)
    cmd_name = parts[0][1:].lower()
    args = parts[1].split() if len(parts) > 1 else []
    
    print(f"[LOG] Command received: {cmd_name} | Args: {args}")
    
    if cmd_name in client.commands:
        try:
            await client.commands[cmd_name]["func"](client, message, args)
            print(f"[LOG] Success execution: {cmd_name}")
        except Exception as e:
            print(f"[ERROR] In command {cmd_name}: {e}")
            await message.edit(f"**Error:** `{e}`")
    else:
        print(f"[LOG] Command {cmd_name} not found in client.commands")

async def main():
    patch_pyrogram()
    for d in ["modules", "loaded_modules"]:
        if not os.path.exists(d): os.makedirs(d)

    session = find_session()
    client = Client(session) if session else await hikka_like_auth()
    
    client.commands = {}
    client.loaded_modules = set()
    client.add_handler(MessageHandler(dispatch_command, filters.me & filters.text))
    
    loader.load_all_modules(client)
    print_banner(get_git_commit())
    print(f"Loaded commands: {list(client.commands.keys())}")
    
    await client.start()
    await idle()
    await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
