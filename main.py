import asyncio
import os
import json
import sys
import subprocess
import time

from pyrogram import Client
from pyrogram import idle
from pyrogram import filters
from pyrogram import utils
from pyrogram.handlers import MessageHandler
from pyrogram.handlers import EditedMessageHandler

import loader

class TerminalLogger:
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("forelka.log", "a", encoding="utf-8")
        self.ignore_list = [
            "PERSISTENT_TIMESTAMP_OUTDATED",
            "updates.GetChannelDifference",
            "RPC_CALL_FAIL",
            "Retrying \"updates.GetChannelDifference\""
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

APP_CONFIG_API_ID = 17349
APP_CONFIG_API_HASH = "344583e45741c457fe1862106095a5eb"

def is_owner(client, user_id):
    path = f"config-{client.me.id}.json"
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                config = json.load(f)
                owners = config.get("owners", [])
                return user_id in owners
        except:
            pass
    return False

async def handler(c, m):
    if not m.text: 
        return
    path = f"config-{c.me.id}.json"
    pref = "."
    if os.path.exists(path):
        try:
            with open(path, "r") as f: 
                pref = json.load(f).get("prefix", ".")
        except: 
            pass
    if not m.text.startswith(pref): 
        return
    parts = m.text[len(pref):].split(maxsplit=1)
    if not parts: 
        return
    cmd = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []
    if cmd in c.commands:
        try: 
            await c.commands[cmd]["func"](c, m, args)
        except Exception as e: 
            print(f"Ошибка в команде {cmd}: {e}")

async def owner_handler(c, m):
    if not m.text or not m.from_user:
        return
    
    if not is_owner(c, m.from_user.id):
        return
    
    path = f"config-{c.me.id}.json"
    pref = "."
    if os.path.exists(path):
        try:
            with open(path, "r") as f: 
                pref = json.load(f).get("prefix", ".")
        except: 
            pass
    
    if not m.text.startswith(pref): 
        return
    
    parts = m.text[len(pref):].split(maxsplit=1)
    if not parts: 
        return
    
    cmd = parts[0].lower()
    args = parts[1].split() if len(parts) > 1 else []
    
    if cmd in c.commands:
        try:
            sent_msg = await c.send_message(m.chat.id, m.text)
            await c.commands[cmd]["func"](c, sent_msg, args)
        except Exception as e:
            pass

async def edited_handler(c, m):
    await handler(c, m)

async def main():
    utils.get_peer_type = lambda x: "channel" if str(x).startswith("-100") else ("chat" if x < 0 else "user")
    
    sess = next((f for f in os.listdir() if f.startswith("forelka-") and f.endswith(".session")), None)
    if sess: 
        client = Client(sess[:-8])
    else:
        api_id, api_hash = APP_CONFIG_API_ID, APP_CONFIG_API_HASH
        temp = Client("temp", api_id=api_id, api_hash=api_hash)
        await temp.start()
        me = await temp.get_me()
        await temp.stop()
        os.rename("temp.session", f"forelka-{me.id}.session")
        client = Client(f"forelka-{me.id}", api_id=api_id, api_hash=api_hash)

    client.commands = {}
    client.loaded_modules = set()
    client.add_handler(MessageHandler(handler, filters.me & filters.text))
    client.add_handler(MessageHandler(owner_handler, ~filters.me & filters.text))
    client.add_handler(EditedMessageHandler(edited_handler, filters.me & filters.text))

    await client.start()
    client.start_time = time.time()
    
    try:
        loader.load_all(client)
        print("Модули загружены успешно")
    except Exception as e:
        print(f"Ошибка загрузки модулей: {e}")

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
User: @{client.me.username if client.me.username else client.me.id}
ID: {client.me.id}
""")

    await idle()
    await client.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nForelka остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
