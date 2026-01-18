import os
import time
import zipfile
import json
from datetime import datetime
from pyrogram.enums import ParseMode

BACKUP_DIR = "backups"


def _load_config(client):
    config_path = f"config-{client.me.id}.json"
    config = {"prefix": "."}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass
    return config, config_path


def _save_config(path, config):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=True)

def is_owner(client, user_id):
    """Проверяет является ли пользователь овнером"""
    config_path = f"config-{client.me.id}.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                owners = config.get("owners", [])
                if client.me.id not in owners:
                    owners.append(client.me.id)
                return user_id in owners
        except:
            pass
    return user_id == client.me.id

def ensure_backup_dir():
    """Создает папку для бекапов если её нет"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def get_files_to_backup():
    """Возвращает список файлов для бекапа"""
    files = []
    
    # Загруженные модули
    if os.path.exists("loaded_modules"):
        for f in os.listdir("loaded_modules"):
            if f.endswith(".py"):
                files.append(os.path.join("loaded_modules", f))
    
    # Конфигурационные файлы
    for f in os.listdir():
        if f.startswith("config-") and f.endswith(".json"):
            files.append(f)
    
    # База данных
    if os.path.exists("forelka.db"):
        files.append("forelka.db")
    
    return files


def create_backup_archive():
    """Создает архив бекапа и возвращает путь + список файлов."""
    ensure_backup_dir()
    files = get_files_to_backup()
    if not files:
        raise ValueError("Нет файлов для бекапа")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}.zip"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            zipf.write(file)
    return backup_path, files


def build_backup_caption(backup_path, files, title="Бекап создан"):
    size = os.path.getsize(backup_path)
    size_mb = size / (1024 * 1024)
    caption = (
        f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>{title}!</b>\n\n"
        f"<b>Размер:</b> <code>{size_mb:.2f} MB</code>\n"
        f"<b>Файлов:</b> <code>{len(files)}</code>\n\n"
        f"<b>Содержимое:</b>\n"
    )
    preview = "\n".join([f"• <code>{f}</code>" for f in sorted(files)[:10]]) or "—"
    caption += preview
    if len(files) > 10:
        caption += f"\n... и ещё {len(files) - 10} файлов"
    caption += "</blockquote>"
    return caption

async def backup_cmd(client, message, args):
    """Создает бекап всех данных"""
    # Проверка прав
    if not is_owner(client, message.from_user.id):
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Доступ запрещен</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    await message.edit(
        "<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Создание бекапа...</b></blockquote>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        backup_path, files = create_backup_archive()
        caption = build_backup_caption(backup_path, files)
        config, _ = _load_config(client)
        chat_id = config.get("log_group_id") or message.chat.id
        thread_id = config.get("log_topic_backups_id")

        await message.delete()
        try:
            await client.send_document(
                chat_id=chat_id,
                document=backup_path,
                caption=caption,
                parse_mode=ParseMode.HTML,
                message_thread_id=thread_id,
            )
        except Exception:
            await client.send_document(
                chat_id=chat_id,
                document=backup_path,
                caption=caption,
                parse_mode=ParseMode.HTML,
            )
        
    except Exception as e:
        await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Ошибка:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

async def restore_cmd(client, message, args):
    """Восстанавливает данные из бекапа"""
    # Проверка прав
    if not is_owner(client, message.from_user.id):
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Доступ запрещен</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    ensure_backup_dir()
    
    # Получаем список бекапов
    backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".zip")]
    
    if not backups:
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Нет доступных бекапов</b>\n\n"
            "Создайте бекап командой: <code>.backup</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    # Если указано имя файла
    if args:
        backup_name = args[0] if args[0].endswith(".zip") else f"{args[0]}.zip"
        if backup_name not in backups:
            return await message.edit(
                f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Бекап не найден:</b> <code>{backup_name}</code></blockquote>",
                parse_mode=ParseMode.HTML
            )
    else:
        # Берем последний бекап
        backups.sort(reverse=True)
        backup_name = backups[0]
    
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    await message.edit(
        f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Восстановление из бекапа...</b>\n\n"
        f"<code>{backup_name}</code></blockquote>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Создаем папку loaded_modules если её нет
        if not os.path.exists("loaded_modules"):
            os.makedirs("loaded_modules")
        
        restored_files = []
        
        # Извлекаем файлы
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            for file in zipf.namelist():
                zipf.extract(file)
                restored_files.append(file)
        
        await message.edit(
            f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Бекап восстановлен!</b>\n\n"
            f"<b>Файл:</b> <code>{backup_name}</code>\n"
            f"<b>Восстановлено файлов:</b> <code>{len(restored_files)}</code>\n\n"
            f"<emoji id=5775887550262546277>❗️</emoji> <b>Перезапустите юзербот для применения изменений!</b>\n\n"
            f"<b>Восстановлено:</b>\n<blockquote expandable>" +
            "\n".join([f"• <code>{f}</code>" for f in sorted(restored_files)]) +
            "</blockquote></blockquote>",
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Ошибка:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

async def backups_cmd(client, message, args):
    """Показывает список доступных бекапов"""
    # Проверка прав
    if not is_owner(client, message.from_user.id):
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Доступ запрещен</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    ensure_backup_dir()
    
    backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".zip")]
    
    if not backups:
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Нет доступных бекапов</b>\n\n"
            "Создайте бекап командой: <code>.backup</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    backups.sort(reverse=True)
    
    text = "<emoji id=5897962422169243693>👻</emoji> <b>Доступные бекапы</b>\n\n"
    
    for backup in backups:
        backup_path = os.path.join(BACKUP_DIR, backup)
        size = os.path.getsize(backup_path)
        size_mb = size / (1024 * 1024)
        
        # Парсим дату из имени файла
        try:
            date_str = backup.replace("backup_", "").replace(".zip", "")
            date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
            date_formatted = date.strftime("%d.%m.%Y %H:%M:%S")
        except:
            date_formatted = "Unknown"
        
        text += f"<blockquote><emoji id=5877468380125990242>➡️</emoji> <code>{backup}</code>\n"
        text += f"<b>Дата:</b> <code>{date_formatted}</code>\n"
        text += f"<b>Размер:</b> <code>{size_mb:.2f} MB</code></blockquote>\n\n"
    
    text += f"<b>Всего:</b> <code>{len(backups)}</code> бекапов\n\n"
    text += "<b>Команды:</b>\n"
    text += "<code>.backup</code> - создать бекап\n"
    text += "<code>.restore [name]</code> - восстановить\n"
    text += "<code>.backups</code> - список бекапов"
    
    await message.edit(text, parse_mode=ParseMode.HTML)

async def delbackup_cmd(client, message, args):
    """Удаляет бекап"""
    # Проверка прав
    if not is_owner(client, message.from_user.id):
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Доступ запрещен</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    if not args:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage:</b> <code>.delbackup [name]</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    backup_name = args[0] if args[0].endswith(".zip") else f"{args[0]}.zip"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    if not os.path.exists(backup_path):
        return await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Бекап не найден:</b> <code>{backup_name}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        os.remove(backup_path)
        await message.edit(
            f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Бекап удален:</b> <code>{backup_name}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Ошибка:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )


async def autobackup_cmd(client, message, args):
    """Настройка автобекапов"""
    config, path = _load_config(client)
    if not args:
        hours = config.get("auto_backup_hours")
        next_ts = config.get("auto_backup_next_ts")
        status = "Отключены"
        if hours:
            status = f"Каждые {hours}h"
        next_info = "—"
        if next_ts:
            next_info = datetime.fromtimestamp(int(next_ts)).strftime("%d.%m.%Y %H:%M:%S")
        return await message.edit(
            f"<emoji id=5897962422169243693>👻</emoji> <b>Автобекапы</b>\n"
            f"<blockquote><b>Статус:</b> <code>{status}</code>\n"
            f"<b>Следующий:</b> <code>{next_info}</code></blockquote>\n\n"
            f"<b>Команды:</b>\n"
            f"<code>.autobackup &lt;hours&gt;</code> — включить\n"
            f"<code>.autobackup off</code> — отключить",
            parse_mode=ParseMode.HTML,
        )

    raw = args[0].lower()
    if raw in {"off", "disable", "0", "нет", "no"}:
        config["auto_backup_disabled"] = True
        config.pop("auto_backup_hours", None)
        config.pop("auto_backup_next_ts", None)
        _save_config(path, config)
        return await message.edit(
            "<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Автобекапы отключены</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    try:
        hours = int(raw)
    except ValueError:
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Неверное значение</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    if hours <= 0:
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Часы должны быть больше нуля</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    config["auto_backup_hours"] = hours
    config["auto_backup_next_ts"] = int(time.time() + hours * 3600)
    config.pop("auto_backup_disabled", None)
    _save_config(path, config)
    await message.edit(
        f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Автобекапы включены</b>\n"
        f"<b>Интервал:</b> <code>{hours}h</code></blockquote>",
        parse_mode=ParseMode.HTML,
    )

def register(app, commands, module_name):
    """Регистрация команд"""
    commands["backup"] = {"func": backup_cmd, "module": module_name}
    commands["restore"] = {"func": restore_cmd, "module": module_name}
    commands["backups"] = {"func": backups_cmd, "module": module_name}
    commands["delbackup"] = {"func": delbackup_cmd, "module": module_name}
    commands["autobackup"] = {"func": autobackup_cmd, "module": module_name}
