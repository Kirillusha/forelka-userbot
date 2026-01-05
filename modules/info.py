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

def upload_to_telegraph(image_url):
    """Загружает изображение на Telegraph и возвращает URL"""
    try:
        # Скачиваем изображение
        response = requests.get(image_url, timeout=10)
        if response.status_code != 200:
            return None
        
        # Загружаем на Telegraph
        files = {'file': ('image.jpg', response.content, 'image/jpeg')}
        upload = requests.post('https://telegra.ph/upload', files=files, timeout=10)
        
        if upload.status_code == 200:
            result = upload.json()
            if isinstance(result, list) and len(result) > 0:
                return f"https://telegra.ph{result[0]['src']}"
    except:
        pass
    return None

async def info_cmd(client, message, args):
    """Информация о юзерботе"""
    
    # Получаем информацию о владельце
    me = client.me
    owner_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    if not owner_name:
        owner_name = "Unknown"
    
    # Загружаем конфигурацию
    config_path = f"config-{me.id}.json"
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except:
            pass
    
    # Получаем настройки
    prefix = config.get("prefix", ".")
    quote_media = config.get("info_quote_media", False)
    banner_url = config.get("info_banner_url", "")
    invert_media = config.get("info_invert_media", False)
    
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
    
    # Формируем текст информации
    info_text = f"""<blockquote><emoji id=5461117441612462242>🔥</emoji> Forelka Userbot</blockquote>

<blockquote><emoji id=5879770735999717115>👤</emoji> Владелец: {owner_name}</blockquote>

<blockquote><emoji id=5778423822940114949>🌿</emoji> Branch: {branch}</blockquote>

<blockquote><emoji id=5877396173135811032>⚙️</emoji> Prefix: «{prefix}»
<emoji id=5778550614669660455>⏱</emoji> Uptime: {uptime_str}</blockquote>

<blockquote><emoji id=5936130851635990622>💾</emoji> RAM usage: {ram_usage_str}
<emoji id=5870982283724328568>🖥</emoji> Host: {hostname}</blockquote>"""
    
    # Определяем тип баннера
    is_web_url = banner_url.startswith(("http://", "https://")) if banner_url else False
    is_local_file = os.path.exists(banner_url) if banner_url and not is_web_url else False
    
    # Параметры для ответа
    reply_to = message.reply_to_message.id if message.reply_to_message else None
    thread_id = message.message_thread_id if hasattr(message, 'message_thread_id') else None
    
    # Удаляем исходное сообщение с командой
    await message.delete()
    
    try:
        if quote_media and is_web_url:
            # Режим Quote Media: отправляем с link preview
            # Добавляем ссылку в самом начале на отдельной строке для превью СВЕРХУ
            text_with_preview = f"<a href=\"{banner_url}\">&#8203;</a>\n{info_text}"
            
            await client.send_message(
                chat_id=message.chat.id,
                text=text_with_preview,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
                reply_to_message_id=reply_to,
                message_thread_id=thread_id
            )
        
        elif is_local_file or (is_web_url and not quote_media):
            # Режим Image Attachment: отправляем фото с caption
            await client.send_photo(
                chat_id=message.chat.id,
                photo=banner_url,
                caption=info_text,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=reply_to,
                message_thread_id=thread_id
            )
        
        else:
            # Fallback: только текст (если нет баннера)
            await client.send_message(
                chat_id=message.chat.id,
                text=info_text,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=reply_to,
                message_thread_id=thread_id
            )
    
    except Exception as e:
        # При ошибке отправляем текст без медиа
        await client.send_message(
            chat_id=message.chat.id,
            text=info_text,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_to,
            message_thread_id=thread_id
        )

async def setinfobanner_cmd(client, message, args):
    """Настройка баннера и quote media для команды info"""
    me = client.me
    config_path = f"config-{me.id}.json"
    
    # Загружаем конфиг
    config = {"prefix": "."}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except:
            pass
    
    # Если нет аргументов - показываем текущие настройки
    if not args:
        quote_media = config.get("info_quote_media", False)
        banner_url = config.get("info_banner_url", "не установлен")
        
        return await message.edit(
            f"<blockquote><emoji id=5897962422169243693>👻</emoji> <b>Info Banner Settings</b>\n\n"
            f"<b>Quote Media:</b> <code>{'✅ Enabled' if quote_media else '❌ Disabled'}</code>\n"
            f"<b>Banner URL:</b> <code>{banner_url}</code>\n\n"
            f"<b>Команды:</b>\n"
            f"<code>.setinfobanner [url]</code> - установить URL баннера\n"
            f"<code>.setinfobanner quote [on/off]</code> - включить/выключить quote media\n"
            f"<code>.setinfobanner clear</code> - удалить баннер</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Обработка команд
    cmd = args[0].lower()
    
    if cmd == "quote":
        # Включение/выключение quote media
        if len(args) < 2:
            return await message.edit(
                "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage:</b> <code>.setinfobanner quote [on/off]</code></blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        state = args[1].lower()
        if state in ["on", "true", "1", "да", "yes"]:
            config["info_quote_media"] = True
            status = "✅ Включен"
        elif state in ["off", "false", "0", "нет", "no"]:
            config["info_quote_media"] = False
            status = "❌ Выключен"
        else:
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Неверное значение. Используйте:</b> <code>on</code> или <code>off</code></blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        
        await message.edit(
            f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Quote Media {status}</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    elif cmd == "clear":
        # Удаление баннера
        if "info_banner_url" in config:
            del config["info_banner_url"]
        if "info_quote_media" in config:
            del config["info_quote_media"]
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        
        await message.edit(
            "<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Настройки баннера удалены</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    else:
        # Установка URL баннера
        banner_url = args[0]
        
        # Проверяем URL
        is_web_url = banner_url.startswith(("http://", "https://"))
        is_local_file = os.path.exists(banner_url)
        
        if not is_web_url and not is_local_file:
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Неверный URL или файл не найден</b></blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        config["info_banner_url"] = banner_url
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        
        banner_type = "🌐 Web URL" if is_web_url else "📁 Local File"
        
        await message.edit(
            f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Баннер установлен!</b>\n\n"
            f"<b>Type:</b> {banner_type}\n"
            f"<b>URL:</b> <code>{banner_url}</code>\n\n"
            f"💡 <b>Tip:</b> Используйте <code>.setinfobanner quote on</code> для включения quote media режима</blockquote>",
            parse_mode=ParseMode.HTML
        )

def register(app, commands, module_name):
    """Регистрация команд"""
    commands["info"] = {"func": info_cmd, "module": module_name}
    commands["setinfobanner"] = {"func": setinfobanner_cmd, "module": module_name}
