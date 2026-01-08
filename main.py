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

def is_owner(client, user_id):
    """Проверяет является ли пользователь овнером"""
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
    """Обработчик команд от самого юзербота"""
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
        except: 
            pass

async def owner_handler(c, m):
    """Обработчик команд от овнеров - юзербот выполняет команду от своего имени"""
    if not m.text or not m.from_user:
        return
    
    # Проверяем что это овнер
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
            # Юзербот отправляет команду от своего имени
            sent_msg = await c.send_message(m.chat.id, m.text)
            # Выполняем команду
            await c.commands[cmd]["func"](c, sent_msg, args)
        except Exception as e:
            pass

async def edited_handler(c, m):
    """Обработчик отредактированных сообщений"""
    await handler(c, m)

async def main():
    utils.get_peer_type = lambda x: "channel" if str(x).startswith("-100") else ("chat" if x < 0 else "user")
    
    sess = next((f for f in os.listdir() if f.startswith("forelka-") and f.endswith(".session")), None)
    if sess: 
        client = Client(sess[:-8])
    else:
        api_id, api_hash = input("API ID: "), input("API HASH: ")
        temp = Client("temp", api_id=api_id, api_hash=api_hash)
        await temp.start()
        me = await temp.get_me()
        await temp.stop()
        os.rename("temp.session", f"forelka-{me.id}.session")
        client = Client(f"forelka-{me.id}", api_id=api_id, api_hash=api_hash)

    client.commands = {}
    client.loaded_modules = set()
    # Обработчик для команд от самого юзербота
    client.add_handler(MessageHandler(handler, filters.me & filters.text))
    # Обработчик для команд от овнеров
    client.add_handler(MessageHandler(owner_handler, ~filters.me & filters.text))
    # Обработчик для отредактированных сообщений
    from pyrogram.handlers import EditedMessageHandler
    client.add_handler(EditedMessageHandler(edited_handler, filters.me & filters.text))

    await client.start()
    client.start_time = time.time()
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
    asyncio.run(main())
