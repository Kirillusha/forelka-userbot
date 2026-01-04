import os
import json
import time
import subprocess
import psutil
from pyrogram.enums import ParseMode

# Сохраним время старта бота
START_TIME = time.time()

async def info_cmd(client, message, args):
    """Информация о юзерботе"""
    
    # Получаем информацию о владельце
    me = await client.get_me()
    owner_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    if not owner_name:
        owner_name = "Unknown"
    
    # Получаем текущий префикс
    path = f"config-{me.id}.json"
    prefix = "."
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                prefix = json.load(f).get("prefix", ".")
        except:
            pass
    
    # Получаем текущую ветку git
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        branch = "unknown"
    
    # Считаем uptime
    uptime_seconds = int(time.time() - START_TIME)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_parts = []
    if days > 0:
        uptime_parts.append(f"{days}д")
    if hours > 0:
        uptime_parts.append(f"{hours}ч")
    if minutes > 0:
        uptime_parts.append(f"{minutes}м")
    uptime_parts.append(f"{seconds}с")
    uptime_str = " ".join(uptime_parts)
    
    # Получаем использование RAM текущим процессом
    process = psutil.Process()
    ram_usage_bytes = process.memory_info().rss
    ram_usage_mb = ram_usage_bytes / (1024 * 1024)
    ram_usage_str = f"{ram_usage_mb:.1f} MB"
    
    # Получаем имя хоста
    try:
        hostname = subprocess.check_output(["hostname"]).decode().strip()
    except:
        hostname = os.uname().nodename if hasattr(os, 'uname') else "Unknown"
    
    # Формируем сообщение
    text = f"""<blockquote>
<emoji document_id=5461117441612462242>🔥</emoji> Forelka Userbot
<blockquote>

<blockquote>
<emoji document_id=5879770735999717115>👤</emoji> Владелец: {owner_name}
</blockquote>

<blockquote>
<emoji document_id=5778423822940114949>🌿</emoji> Branch: {branch}
</blockquote>

<blockquote>
<emoji document_id=5877396173135811032>⚙️</emoji> Prefix: «{prefix}»

<emoji document_id=5778550614669660455>⏱</emoji> Uptime: {uptime_str}
</blockquote>


<blockquote>
<emoji document_id=5936130851635990622>💾</emoji> RAM usage: {ram_usage_str}

<emoji document_id=5870982283724328568>🖥</emoji> Host: {hostname}
</blockquote>
</blockquote>"""
    
    await message.edit(text, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    """Регистрация команды"""
    commands["info"] = {"func": info_cmd, "module": module_name}
