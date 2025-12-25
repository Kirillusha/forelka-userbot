import os
import time
import psutil
import json
import subprocess
from datetime import timedelta
from pyrogram.enums import ParseMode

start_time = time.time()

def get_git_info():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.STDOUT).decode().strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.STDOUT).decode().strip()
        return commit, branch, False
    except:
        return "unknown", "unknown", False

async def info_cmd(client, message, args):
    try:
        me = await client.get_me()
        path = f"config-{me.id}.json"

        pref = "."
        if os.path.exists(path):
            with open(path, "r") as f:
                try: 
                    cfg = json.load(f)
                    pref = cfg.get("prefix", ".")
                except: pass

        commit, branch, update_available = get_git_info()
        
        uptime_sec = time.time() - start_time
        uptime = str(timedelta(seconds=int(uptime_sec)))
        
        cpu = psutil.cpu_percent(interval=None)
        if cpu is None: cpu = 0.0
        
        ram = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        text = (
            f"<emoji document_id=5073781154667037412>🥇</emoji><b> Владелец:</b> <a href='tg://user?id={me.id}'><b>{me.first_name}</b></a>\n\n"
            f"<emoji document_id=5073384402768102367>💝</emoji><b> Версия:</b> <i>Release Catalystic</i> <a href='https://github.com/whymakser/forelka-userbot/commit/{commit}'>#{commit}</a>\n"
            f"<emoji document_id=5073480266438148710>🥰</emoji><b> Ветка:</b> {branch}\n"
        )

        if update_available:
            text += f"<emoji id=5879813604068298387>❗️</emoji> <b>Требуется обновление</b> <code>{pref}update</code>\n\n"
        else:
            text += "<b>Обновлений не требуется</b>\n\n"

        text += (
            f"<emoji document_id=5071243121052877494>😍</emoji><b> Префикс:</b> «<code>{pref}</code>»\n"
            f"<emoji document_id=5073605116842476142>😐</emoji><b> Аптайм:</b> {uptime}\n\n"
            f"<emoji document_id=5073768935485080807>👍</emoji><b> Использование CPU:</b> {cpu}%\n"
            f"<emoji document_id=5073510468648174086>🚨</emoji><b> Использование RAM:</b> {ram:.1f} MB"
        )

        await message.edit(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        await message.edit(f"<b>Ошибка:</b>\n<code>{e}</code>")

def register(app, commands, module_name):
    commands["info"] = {"func": info_cmd, "module": module_name}
