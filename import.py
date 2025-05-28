import os
import importlib.util
from pyrogram import filters
from pyrogram.types import Message

MODULES_DIR = "modules"

async def dlm_command(client, message: Message, args):
    # Проверяем, есть ли прикреплённый файл
    if not message.reply_to_message:
        await message.reply("❗️ Пожалуйста, ответьте командой .dlm на сообщение с файлом .py")
        return
    
    reply = message.reply_to_message
    if not reply.document:
        await message.reply("❗️ В ответном сообщении должен быть файл с модулем (.py)")
        return
    
    file_name = reply.document.file_name
    if not file_name.endswith(".py"):
        await message.reply("❗️ Файл должен иметь расширение .py")
        return
    
    # Убедимся, что папка modules существует
    if not os.path.exists(MODULES_DIR):
        os.makedirs(MODULES_DIR)
    
    # Сохраняем файл
    file_path = os.path.join(MODULES_DIR, file_name)
    await reply.download(file_path)
    
    # Импортируем модуль динамически
    module_name = file_name[:-3]
    
    # Попытка загрузить модуль
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Предполагается, что в модуле есть функция register(app, commands, prefix, module_name)
        if hasattr(module, "register"):
            module.register(client, client.commands, client.prefix, module_name)
        else:
            await message.reply("⚠️ Модуль загружен, но в нем отсутствует функция register.")
            return
        
        await message.reply(f"✅ Модуль `{module_name}` успешно загружен и зарегистрирован.")
    except Exception as e:
        await message.reply(f"❌ Ошибка при загрузке модуля:\n`{e}`")

def register(app, commands, prefix, module_name):
    commands["dlm"] = {
        "func": dlm_command,
        "desc": "Загрузить и подключить модуль из файла (ответом на файл .py)",
        "module": module_name
    }