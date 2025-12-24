import asyncio
import os
import sys
import subprocess
from pyrogram import Client, filters, idle
import import

def get_git_commit():
    try:
        result = subprocess.run(["git", "log", "--oneline", "-1", "--format=%h"], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return "unknown"

def check_git_update():
    try:
        subprocess.run(["git", "fetch"], capture_output=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        local = subprocess.run(["git", "rev-parse", "@"], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        remote = subprocess.run(["git", "rev-parse", "@{u}"], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        base = subprocess.run(["git", "merge-base", "@", "@{u}"], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if local.stdout.strip() == remote.stdout.strip():
            return False, "No update needed"
        elif local.stdout.strip() == base.stdout.strip():
            return True, "Update available!"
        else:
            return False, "Diverged"
    except:
        return False, "Git check failed"

def find_session():
    for file in os.listdir():
        if file.startswith("forelka-") and file.endswith(".session"):
            return file.replace(".session", "")
    return None

async def hikka_like_auth():
    print("Restarting...")
    print()
    
    api_id = input("API ID: ").strip()
    api_hash = input("API Hash: ").strip()
    phone = input("Phone: ").strip()
    
    client = Client("forelka", int(api_id), api_hash)
    
    await client.connect()
    sent_code = await client.send_code(phone)
    
    code = input("Code: ").strip()
    
    try:
        await client.sign_in(phone, sent_code.phone_code_hash, code)
    except Exception as e:
        if "password" in str(e):
            password = input("2FA password: ").strip()
            await client.check_password(password)
        else:
            raise e
    
    me = await client.get_me()
    user_id = me.id
    
    old_session = "forelka.session"
    new_session = f"forelka-{user_id}.session"
    
    if os.path.exists(old_session):
        os.rename(old_session, new_session)
        if os.path.exists(old_session + ".journal"):
            os.rename(old_session + ".journal", new_session + ".journal")
    
    print("Restarting...")
    return Client(new_session)

async def main():
    session_name = find_session()
    
    if session_name:
        client = Client(session_name)
    else:
        client = await hikka_like_auth()
    
    commands = {}
    client.commands = commands
    
    import.load_all_modules(client, commands, ".")
    
    @client.on_message(filters.command("help", prefixes=".") & filters.me)
    async def help_command(client, message):
        response = "Commands:\n"
        for cmd, info in commands.items():
            response += f"{cmd}: {info.get('desc', 'No description')}\n"
        await message.reply(response)
    
    @client.on_message(filters.command("reload", prefixes=".") & filters.me)
    async def reload_all_command(client, message):
        for module_name in list(import.loaded_modules.keys()):
            import.unload_module(commands, module_name)
        
        import.load_all_modules(client, commands, ".")
        await message.reply("All modules reloaded")
    
    current_commit = get_git_commit()
    needs_update, update_status = check_git_update()
    
    print("  __               _ _         ")
    print(" / _|             | | |        ")
    print("| |_ ___  _ __ ___| | | ____ _ ")
    print("|  _/ _ \\| '__/ _ \\ | |/ / _` |")
    print("| || (_) | | |  __/ |   < (_| |")
    print("|_| \\___/|_|  \\___|_|_|\\_\\__,_|")
    print("                               ")
    print("Forelka Started")
    print(f"Git: #{current_commit}")
    
    if needs_update:
        print("Update available!")
    else:
        print(update_status)
    
    await client.start()
    await idle()

if __name__ == "__main__":
    asyncio.run(main())