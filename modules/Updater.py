import os
import sys
import time
import asyncio
import subprocess
from pyrogram.enums import ParseMode

async def update_cmd(client, message, args):
    try:
        await message.edit("<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Updating...</b></blockquote>", parse_mode=ParseMode.HTML)
        res = subprocess.check_output(["git", "pull"]).decode()
        if "Already up to date" in res:
            return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Already up to date</b></blockquote>", parse_mode=ParseMode.HTML)
        
        os.environ["RESTART_INFO"] = f"{time.time()}|{message.chat.id}|{message.id}"
        os.execv(sys.executable, [sys.executable, "main.py"])
    except Exception as e:
        await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>", parse_mode=ParseMode.HTML)

async def restart_cmd(client, message, args):
    os.environ["RESTART_INFO"] = f"{time.time()}|{message.chat.id}|{message.id}"
    await message.edit("<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Restarting...</b></blockquote>", parse_mode=ParseMode.HTML)
    os.execv(sys.executable, [sys.executable, "main.py"])

def register(app, commands, module_name):
    commands["update"] = {"func": update_cmd, "module": module_name}
    commands["restart"] = {"func": restart_cmd, "module": module_name}
    
    restart_data = os.environ.get("RESTART_INFO")
    if restart_data:
        try:
            start_time, chat_id, msg_id = restart_data.split("|")
            diff = time.time() - float(start_time)
            
            async def notify():
                await asyncio.sleep(1.5)
                await app.edit_message_text(
                    int(chat_id), 
                    int(msg_id), 
                    f"<emoji id=5897962422169243693>👻</emoji> <b>Forelka Started</b>\n"
                    f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Restart time:</b> <code>{diff:.2f}s</code></blockquote>",
                    parse_mode=ParseMode.HTML
                )
            
            asyncio.get_event_loop().create_task(notify())
            os.environ.pop("RESTART_INFO", None)
        except:
            pass
