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

    path = f"config-{m.from_user.id}.json"
    pref = "." 
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                cfg = json.load(f)
                pref = cfg.get("prefix", ".")
            except: pass

    if not m.text.startswith(pref): return

    cmd_part = m.text[len(pref):].split(maxsplit=1)
    if not cmd_part: return

    cmd = cmd_part[0].lower()
    args = cmd_part[1].split() if len(cmd_part) > 1 else []

    if cmd in c.commands:
        try: 
            await c.commands[cmd]["func"](c, m, args)
        except Exception: 
            pass

async def main():
    utils.get_peer_type = lambda x: "channel" if str(x).startswith("-100") else ("chat" if x < 0 else "user")
    
    sess_file = next((f for f in os.listdir() if f.startswith("forelka-") and f.endswith(".session")), None)
    
    if sess_file:
        sess_name = sess_file[:-8]
    else:
        temp_client = Client("temp_session")
        await temp_client.start()
        me = await temp_client.get_me()
        user_id = me.id
        await temp_client.stop()
        
        sess_name = f"forelka-{user_id}"
        os.rename("temp_session.session", f"{sess_name}.session")

    client = Client(sess_name)
    client.commands, client.loaded_modules = {}, set()

    client.add_handler(MessageHandler(handler, filters.me & filters.text))

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
    loader.load_all(client)
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
