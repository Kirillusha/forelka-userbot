from pyrogram.types import Message

def get_command_from_message(message: Message, prefix: str):
    """
    Извлекает команду и аргументы из текста сообщения с учетом префикса.
    Возвращает tuple (command, args) или None.
    """
    if not message.text:
        return None

    text = message.text.strip()
    if not text.startswith(prefix):
        return None

    parts = text[len(prefix):].split()
    if not parts:
        return None

    command = parts[0].lower()
    args = parts[1:]
    return command, args