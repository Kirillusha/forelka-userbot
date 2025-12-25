import platform
import os
import time
import psutil
import json
import subprocess
from datetime import datetime
from pyrogram.enums import ParseMode
from pyrogram.types import InputMediaPhoto

start_time = time.time()

def get_git_info():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
        subprocess.run(["git", "fetch"], capture_output=True)
        status = subprocess.check_output(["git", "status", "-uno"]).decode()
        needs_update = "Your branch is behind" in status
        return commit, branch, needs_update
    except:
        return "unknown", "unknown", False

async def info_cmd(client, message, args):
    me = await client.get_me()
    path = f"config-{me.id}.json"
    cfg = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            try: cfg = json.load(f)
            except: pass

    pref = cfg.get("prefix", ".")
    banner_url = cfg.get("banner_url")
    commit, branch, update_available = get_git_info()
    uptime_sec = int(time.time() - start_time)
    uptime = str(datetime.utcfromtimestamp(uptime_sec).strftime('%H:%M:%S'))
    cpu = psutil.cpu_percent()
    ram = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

    text = (
        f"<emoji document_id=5373141891321699086>😎</emoji><b> Владелец:</b> <a href='tg://user?id={me.id}'><b>{me.first_name}</b></a>\n\n"
        f"<emoji document_id=5469741319330996757>💫</emoji><b> Версия:</b> <i>Release Catalystic</i> <a href='https://github.com/whymakser/forelka-userbot/commit/{commit}'>#{commit}</a>\n"
        f"<emoji document_id=5449918202718985124>🌳</emoji><b> Ветка:</b> {branch}\n"
    )
    
    if update_available:
        text += f"<emoji id=5879813604068298387>❗️</emoji> <b>Требуется обновление</b> <code>{pref}update</code>\n\n"
    else:
        text += "<b>Обновлений не требуется</b>\n\n"

    text += (
        f"<emoji document_id=5472111548572900003>⌨️</emoji><b> Префикс:</b> «<code>{pref}</code>»\n"
        f"<emoji document_id=5451646226975955576>⌛️</emoji><b> Аптайм:</b> {uptime}\n\n"
        f"<emoji document_id=5431449001532594346>⚡️</emoji><b> Использование CPU:</b> {cpu}%\n"
        f"<emoji document_id=5359785904535774578>💼</emoji><b> Использование RAM:</b> {ram:.1f} MB"
    )

    if banner_url:
        if message.photo or message.caption:
            try:
                await message.edit_media(
                    media=InputMediaPhoto(banner_url, caption=text),
                    parse_mode=ParseMode.HTML
                )
                return
            except: pass
        
        try:
            await client.send_photo(message.chat.id, banner_url, caption=text, parse_mode=ParseMode.HTML)
            await message.delete()
        except:
            await message.edit(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        await message.edit(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def fi_cmd(client, message, args):
    if not args:
        return await message.edit("<emoji id=5879813604068298387>❗️</emoji> <b>Укажите ссылку</b>", parse_mode=ParseMode.HTML)
    url = args[0]
    me = await client.get_me()
    path = f"config-{me.id}.json"
    cfg = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            try: cfg = json.load(f)
            except: pass
    cfg["banner_url"] = url
    with open(path, "w") as f:
        json.dump(cfg, f, indent=4)
    await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Баннер сохранен</b></blockquote>", parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["info"] = {"func": info_cmd, "module": module_name}
    commands["fi"] = {"func": fi_cmd, "module": module_name}
