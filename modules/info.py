import os
import json
import time
import subprocess
import requests
from pyrogram.enums import ParseMode

try:
    import psutil
    HAS_PSUTIL = True
except:
    HAS_PSUTIL = False

# URL изображения по умолчанию (можно изменить в config)
DEFAULT_IMAGE_URL = "https://raw.githubusercontent.com/username/repo/main/forelka.jpg"

async def info_cmd(client, message, args):
    """Информация о юзерботе"""
    
    # Получаем информацию о владельце
    me = client.me
    owner_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    if not owner_name:
        owner_name = "Unknown"
    
    # Получаем текущий префикс и URL изображения
    path = f"config-{me.id}.json"
    prefix = "."
    image_url = None
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                cfg = json.load(f)
                prefix = cfg.get("prefix", ".")
                image_url = cfg.get("info_image", None)
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
    start_time = getattr(client, 'start_time', time.time())
    uptime_seconds = int(time.time() - start_time)
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
    if HAS_PSUTIL:
        try:
            process = psutil.Process()
            ram_usage_bytes = process.memory_info().rss
            ram_usage_mb = ram_usage_bytes / (1024 * 1024)
            ram_usage_str = f"{ram_usage_mb:.1f} MB"
        except:
            ram_usage_str = "N/A"
    else:
        ram_usage_str = "N/A"
    
    # Получаем имя хоста
    try:
        hostname = subprocess.check_output(["hostname"]).decode().strip()
    except:
        hostname = os.uname().nodename if hasattr(os, 'uname') else "Unknown"
    
    # Формируем сообщение
    text = f"""<blockquote><emoji id=5461117441612462242>🔥</emoji> Forelka Userbot</blockquote>

<blockquote><emoji id=5879770735999717115>👤</emoji> Владелец: {owner_name}</blockquote>

<blockquote><emoji id=5778423822940114949>🌿</emoji> Branch: {branch}</blockquote>

<blockquote><emoji id=5877396173135811032>⚙️</emoji> Prefix: «{prefix}»
<emoji id=5778550614669660455>⏱</emoji> Uptime: {uptime_str}</blockquote>

<blockquote><emoji id=5936130851635990622>💾</emoji> RAM usage: {ram_usage_str}
<emoji id=5870982283724328568>🖥</emoji> Host: {hostname}</blockquote>"""
    
    # Если есть URL изображения, отправляем с фото
    if image_url:
        try:
            # Скачиваем изображение
            image_path = "temp_info_image.jpg"
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                with open(image_path, "wb") as f:
                    f.write(response.content)
                
                # Удаляем старое сообщение и отправляем новое с фото
                await message.delete()
                await client.send_photo(
                    message.chat.id,
                    image_path,
                    caption=text,
                    parse_mode=ParseMode.HTML
                )
                
                # Удаляем временный файл
                if os.path.exists(image_path):
                    os.remove(image_path)
            else:
                # Если не удалось загрузить, просто отправляем текст
                await message.edit(text, parse_mode=ParseMode.HTML)
        except:
            # Если произошла ошибка, просто отправляем текст
            await message.edit(text, parse_mode=ParseMode.HTML)
    else:
        # Без изображения
        await message.edit(text, parse_mode=ParseMode.HTML)

async def setinfoimg_cmd(client, message, args):
    """Установка изображения для команды info"""
    me = client.me
    path = f"config-{me.id}.json"
    
    # Загружаем текущий конфиг
    cfg = {"prefix": "."}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                cfg = json.load(f)
        except:
            pass
    
    # Если нет аргументов, показываем текущую настройку
    if not args:
        current = cfg.get("info_image", "не установлено")
        return await message.edit(
            f"<blockquote><emoji id=5897962422169243693>👻</emoji> <b>Info Image</b>\n\n"
            f"<b>Текущее изображение:</b>\n<code>{current}</code>\n\n"
            f"<b>Использование:</b>\n"
            f"<code>.setinfoimg [url]</code> - установить изображение\n"
            f"<code>.setinfoimg clear</code> - убрать изображение</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Если "clear", удаляем изображение
    if args[0].lower() == "clear":
        if "info_image" in cfg:
            del cfg["info_image"]
        with open(path, "w") as f:
            json.dump(cfg, f, indent=4)
        return await message.edit(
            "<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Изображение удалено</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Устанавливаем новый URL
    new_url = args[0]
    
    # Проверяем доступность изображения
    try:
        response = requests.head(new_url, timeout=5)
        if response.status_code != 200:
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Не удалось загрузить изображение по этой ссылке</b></blockquote>",
                parse_mode=ParseMode.HTML
            )
    except:
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Не удалось проверить ссылку</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Сохраняем
    cfg["info_image"] = new_url
    with open(path, "w") as f:
        json.dump(cfg, f, indent=4)
    
    await message.edit(
        f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Изображение установлено!</b>\n\n"
        f"<code>{new_url}</code></blockquote>",
        parse_mode=ParseMode.HTML
    )

def register(app, commands, module_name):
    """Регистрация команды"""
    commands["info"] = {"func": info_cmd, "module": module_name}
    commands["setinfoimg"] = {"func": setinfoimg_cmd, "module": module_name}
