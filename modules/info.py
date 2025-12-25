import os
import time
import psutil
import json
import subprocess
from datetime import timedelta
from pyrogram.enums import ParseMode

start_time = time.time()

async def info_cmd(client, message, args):
    try:
        me = await client.get_me()
        user_id = me.id if me else "unknown"
        first_name = me.first_name if me else "User"
        
        pref = "."
        try:
            path = f"config-{user_id}.json"
            if os.path.exists(path):
                with open(path, "r") as f:
                    cfg = json.load(f)
                    pref = cfg.get("prefix", ".")
        except: pass

        commit, branch = "unknown", "unknown"
        try:
            commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.STDOUT).decode().strip()
            branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.STDOUT).decode().strip()
        except: pass

        uptime = str(timedelta(seconds=int(time.time() - start_time)))
        cpu = psutil.cpu_percent() or 0
        ram = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        text = (
            f"<emoji document_id=5373141891321699086>😎</emoji><b> Владелец:</b> <a href='tg://user?id={user_id}'><b>{first_name}</b></a>\n\n"
            f"<emoji document_id=5469741319330996757>💫</emoji><b> Версия:</b> <i>Release Catalystic</i> <a href='https://github.com/whymakser/forelka-userbot/commit/{commit}'>#{commit}</a>\n"
            f"<emoji document_id=5449918202718985124>🌳</emoji><b> Ветка:</b> {branch}\n\n"
            f"<emoji document_id=5472111548572900003>⌨️</emoji><b> Префикс:</b> «<code>{pref}</code>»\n"
            f"<emoji document_id=5451646226975955576>⌛️</emoji><b> Аптайм:</b> {uptime}\n\n"
            f"<emoji document_id=5431449001532594346>⚡️</emoji><b> Использование CPU:</b> {cpu}%\n"
            f"<emoji document_id=5359785904535774578>💼</emoji><b> Использование RAM:</b> {ram:.1f} MB"
        )

        await message.edit(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        await message.edit(f"<b>Пиздец:</b> <code>{str(e)}</code>")

def register(app, commands, module_name):
    commands["info"] = {"func": info_cmd, "module": module_name}
