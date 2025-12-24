import asyncio
import os
import sys
from pyrogram import Client, idle, filters
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
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"

def find_session():
    for f in os.listdir():
        if f.startswith("forelka-") and f.endswith(".session"):
            return f[:-8]
    return None

async def hikka_like_auth():
    api_id = int(input("API ID: ").strip())
    api_hash = input("API Hash: ").strip()
    phone = input("Phone: ").strip()

    client = Client("forelka", api_id=api_id, api_hash=api_hash)
    await client.connect()

    sent = await client.send_code(phone)
    code = input("Code: ").strip()

    try:
        await client.sign_in(phone, sent.phone_code_hash, code)
    except Exception:
        pwd = input("2FA password: ").strip()
        await client.check_password(pwd)

    me = await client.get_me()
    name = f"forelka-{me.id}"
    client.storage.rename(name)
    await client.disconnect()

    return Client(name, api_id=api_id, api_hash=api_hash)

async def dispatch_command(client, message):
    if not message.text or not message.text.startswith("."):
        return

    parts = message.text.split(maxsplit=1)
    cmd_name = parts[0][1:].lower()
    args = parts[1].split() if len(parts) > 1 else []

    if cmd_name in client.commands:
        await client.commands[cmd_name]["func"](client, message, args)

async def main():
    session = find_session()
    if session:
        client = Client(session)
    else:
        client = await hikka_like_auth()

    # Инициализация хранилищ в объекте клиента
    client.commands = {}
    client.loaded_modules = set()

    # Регистрация глобального обработчика команд
    client.add_handler(
        MessageHandler(
            dispatch_command, 
            filters.me & filters.text
        )
    )

    # Загрузка модулей
    loader.load_all_modules(client)

    print_banner(get_git_commit())

    await client.start()
    await idle()
    await client.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
