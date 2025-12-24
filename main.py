import asyncio
import os
import loader
import subprocess
from pyrogram import Client, idle, filters, utils
from pyrogram.handlers import MessageHandler

def get_commit():
    try: 
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except: 
        return "unknown"

async def handler(c, m):
    if not m.text or not m.text.startswith("."): return
    parts = m.text.split()
    cmd = parts[0][1:].lower()
    if cmd in c.commands:
        try: 
            await c.commands[cmd]["func"](c, m, parts[1:])
        except Exception: 
            pass

async def main():
    utils.get_peer_type = lambda x: "channel" if str(x).startswith("-100") else ("chat" if x < 0 else "user")
    sess = next((f[:-8] for f in os.listdir() if f.startswith("forelka-") and f.endswith(".session")), None)
    if not sess: return

    client = Client(sess)
    client.commands, client.loaded_modules = {}, set()
    client.add_handler(MessageHandler(handler, filters.me & filters.text))
    
    loader.load_all(client)
    
    print("  __               _ _         ")
    print(" / _|             | | |        ")
    print("| |_ ___  _ __ ___| | | ____ _ ")
    print("|  _/ _ \\| '__/ _ \\ | |/ / _` |")
    print("| || (_) | | |  __/ |   < (_| |")
    print("|_| \\___/|_|  \\___|_|_|\\_\\__,_|")
    print("                               ")
    print("Forelka Started")
    print(f"Git: #{get_commit()}")
    print()
    
    await client.start()
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
