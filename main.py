import asyncio
import os
import json
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
    if not m.text: return
    
    pref = "."
    path = f"config-{c.me.id}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            try: pref = json.load(f).get("prefix", ".")
            except: pass
    
    if not m.text.startswith(pref): return
    
    parts = m.text[len(pref):].split(maxsplit=1)
    if not parts: return
    
    cmd = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []
    
    if cmd in c.commands:
        try: await c.commands[cmd]["func"](c, m, args)
        except: pass

async def main():
    utils.get_peer_type = lambda x: "channel" if str(x).startswith("-100") else ("chat" if x < 0 else "user")

    sess_file = next((f for f in os.listdir() if f.startswith("forelka-") and f.endswith(".session")), None)

    if sess_file:
        client = Client(sess_file[:-8])
    else:
        api_id, api_hash = input("API ID: "), input("API HASH: ")
        temp = Client("temp_session", api_id=api_id, api_hash=api_hash)
        await temp.start()
        me = await temp.get_me()
        await temp.stop()
        os.rename("temp_session.session", f"forelka-{me.id}.session")
        client = Client(f"forelka-{me.id}", api_id=api_id, api_hash=api_hash)

    client.commands, client.loaded_modules = {}, set()
    client.add_handler(MessageHandler(handler, filters.me & filters.text))

    print(r"""
  __               _ _         
 / _|             | | |        
| |_ ___  _ __ ___| | | ____ _ 
|  _/ _ \| '__/ _ \ | |/ / _` |
| || (_) | | |  __/ |   < (_| |
|_| \___/|_|  \___|_|_|\_\__,_|
    """)
    print(f"Forelka Started | Git: #{get_commit()}\n")

    await client.start()
    loader.load_all(client)
    await idle()

if __name__ == "__main__":
    asyncio.run(main())