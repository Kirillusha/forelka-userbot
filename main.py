import configparser
import sys
import logging
import importlib
from pyrogram import Client, filters
from pyrogram.types import Message
from utils import get_command_from_message
from modules.loader import ModuleLoader
from database import Database

commands = {}

logging.basicConfig(
    filename='forelka.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    encoding='utf-8'
)

config = configparser.ConfigParser()
config.read("config.ini")

api_id = int(config["pyrogram"]["api_id"])
api_hash = config["pyrogram"]["api_hash"]
session_name = config["pyrogram"]["session_name"]
default_prefix = config["pyrogram"].get("command_prefix", "/")

owner_id = int(config["pyrogram"].get("owner_id", 0))
if owner_id == 0:
    raise ValueError("В config.ini не указан owner_id — ID владельца юзербота")

db = Database()

app = Client(session_name, api_id=api_id, api_hash=api_hash)

commands = {}

prefix = db.get("prefix", default_prefix)
app.prefix = prefix
app.db = db

loader = ModuleLoader(app, commands, app.prefix)
loader.load_modules()

async def reload_command(client, message: Message, args):
    reloaded_count = 0
    for module_name, module in list(sys.modules.items()):
        if module_name and module_name.startswith("modules"):
            try:
                importlib.reload(module)
                reloaded_count += 1
            except Exception:
                pass
    await message.reply(f"Перезагружено {reloaded_count} модулей.")

commands["reload"] = {
    "func": reload_command,
    "desc": "Перезагрузить все модули",
    "module": "system"
}

@app.on_message(filters.me & filters.text)
async def handler(client: Client, message: Message):
    if message.from_user is None or message.from_user.id != owner_id:
        return

    cmd_data = get_command_from_message(message, client.prefix)
    if not cmd_data:
        return
    command, args = cmd_data
    cmd_info = commands.get(command)
    if cmd_info:
        await cmd_info["func"](client, message, args)

def print_banner():
    banner = r"""
 ______   _______  ______   _______  __   __  __   __ 
|      | |       ||      | |       ||  |_|  ||  |_|  |
|  _    ||   _   ||  _    ||   _   ||       ||       |
| | |   ||  | |  || | |   ||  | |  ||       ||       |
| |_|   ||  |_|  || |_|   ||  |_|  ||       ||       |
|       ||       ||       ||       || ||_|| || ||_|| |
|______| |_______||______| |_______||_|   |_||_|   |_|
                                                         
"""
    print(banner)


if __name__ == "__main__":
    print_banner()
    print(f"Юзербот Forelka запущен! Текущий префикс: {app.prefix}")
    try:
        app.run()
    finally:
        db.close()