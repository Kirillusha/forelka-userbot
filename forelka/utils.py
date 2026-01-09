from pyrogram.types import Message

def get_command_from_message(message: Message, prefix: str):
    if not message.text or not message.text.startswith(prefix):
        return None
    
    parts = message.text[len(prefix):].split()
    if not parts:
        return None
    
    return parts[0].lower(), parts[1:]
