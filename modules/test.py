# test.py - тестовый модуль для загрузки через .dlm

def register(app, commands, prefix, module_name):
    """
    Регистрация команд для этого модуля.
    """
    async def test_command(client, message, args):
        await message.reply("Тест прошёл!")

    # Добавляем команду 'test' с этой функцией
    commands["test"] = {
        "func": test_command,
        "desc": "Тестовая команда, чтобы проверить загрузку модуля",
        "module": module_name
    }
