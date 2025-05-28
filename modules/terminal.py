import asyncio
import shlex
from pyrogram.types import Message

async def terminal(client, message: Message, args):
    if not args:
        await message.edit_text("Пожалуйста, укажите команду для выполнения.")
        return
    
    command_str = " ".join(args)
    try:
        # Разбираем команду на части
        # Изначально можем сразу использовать shell-команду
        # но для безопасности и гибкости лучше использовать create_subprocess_shell
        process = await asyncio.create_subprocess_shell(
            command_str,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        output = stdout.decode().strip()
        error = stderr.decode().strip()

        if output:
            response = f"🟢 Результат:\n{output}"
        elif error:
            response = f"🔴 Ошибка:\n{error}"
        else:
            response = "Команда выполнена, но вывод пуст."

        max_length = 4000
        for i in range(0, len(response), max_length):
            chunk = response[i:i+max_length]
            try:
                # Если редактируем первый раз, отправляем message.edit_text
                await message.edit_text(chunk)
            except Exception:
                # Если редактировать нельзя (например, первый раз), отправляем
                # и сохраняем это сообщение для последующих правок
                message = await message.edit_text(chunk)
        
    except Exception as e:
        try:
            await message.edit_text(f"Ошибка при выполнении команды: {e}")
        except Exception:
            await message.reply(f"Ошибка при выполнении команды: {e}")

def register(app, commands, prefix, module_name):
    commands["terminal"] = {
        "func": terminal,
        "desc": "Выполнить команду в терминале хостинга и вернуть результат",
        "module": module_name
    }