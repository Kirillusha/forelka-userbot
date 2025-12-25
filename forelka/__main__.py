import asyncio
import os
import json
import sys
import subprocess

from pyrogram import Client
from pyrogram import idle
from pyrogram import filters
from pyrogram import utils
from pyrogram.handlers import MessageHandler

from . import loader

class TerminalLogger:
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("forelka.log", "a", encoding="utf-8")
        self.ignore_list = [
            "PERSISTENT_TIMESTAMP_OUTDATED",
            "updates.GetChannelDifference",
            "RPC_CALL_FAIL",
            "Retrying \"updates.GetChannelDifference\"",
            "disable_web_page_preview"
        ]

    def write(self, m):
        if not m.strip():
            return
        if any(x in m for x in self.ignore_list):
            return
        self.terminal.write(m)
        self.log.write(m)
        self.log.flush()

    def flush(self): 
        pass

sys.stdout = sys.stderr = TerminalLogger()

async def handler(c, m):
    if not m.text: 
        return
    
    path = f"config-{c.me.id}.json"
    conf = {"prefix": ".", "aliases": {}}
    
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                conf.update(json.load(f))
        except:
            pass

    pref = conf.get("prefix", ".")
    if not m.text.startswith(pref): 
        return
        
    parts = m.text[len(pref):].split(maxsplit=1)
    if not parts: 
        return
        
    cmd = parts[0].lower()
    
    aliases = conf.get("aliases", {})
    if cmd in aliases:
        cmd = aliases[cmd]
        
    args = parts[1].split() if len(parts) > 1 else []
    
    if cmd in c.commands:
        try: 
            await c.commands[cmd]["func"](c, m, args)
        except: 
            pass

async def main():
    utils.get_peer_type = lambda x: "channel" if str(x).startswith("-100") else ("chat" if x < 0 else "user")
    sess_file = next((f for f in os.listdir(".") if f.startswith("forelka-") and f.endswith(".session")), None)

    if sess_file:
        sess_name = sess_file[:-8]
        client = Client(name=sess_name, workdir=".")
    else:
        api_id = input("API ID: ")
        api_hash = input("API HASH: ")
        temp = Client("temp", api_id=api_id, api_hash=api_hash, workdir=".")
        await temp.start()
        me = await temp.get_me()
        await temp.stop()
        new_name = f"forelka-{me.id}"
        if os.path.exists("temp.session"):
            os.rename("temp.session", f"{new_name}.session")
        client = Client(name=new_name, api_id=api_id, api_hash=api_hash, workdir=".")

    client.commands = {}
    client.loaded_modules = set()
    client.add_handler(MessageHandler(handler, filters.me & filters.text))

    await client.start()

    path = f"config-{client.me.id}.json"
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                client.prefix = json.load(f).get("prefix", ".")
        except:
            client.prefix = "."
    else:
        client.prefix = "."

    loader.load_all(client)

    git = "unknown"
    try: 
        git = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except: 
        pass

    print(fr"""
  __               _ _         
 / _|             | | |        
| |_ ___  _ __ ___| | | ____ _ 
|  _/ _ \| '__/ _ \ | |/ / _` |
| || (_) | | |  __/ |   < (_| |
|_| \___/|_|  \___|_|_|\_\__,_|

Forelka Started | Git: #{git}
""")

    await idle()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
