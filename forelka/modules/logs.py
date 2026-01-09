import os
from pyrogram.enums import ParseMode

async def log_cmd(client, message, args):
    log_file = "forelka.log"
    if not os.path.exists(log_file):
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Log file not found</b></blockquote>", parse_mode=ParseMode.HTML)

    await message.edit("<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Sending logs...</b></blockquote>", parse_mode=ParseMode.HTML)
    await client.send_document("me", log_file, caption="<emoji id=5897962422169243693>👻</emoji> <b>Forelka Logs</b>")
    await message.edit("<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Logs sent to Saved Messages</b></blockquote>", parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["log"] = {"func": log_cmd, "module": module_name}
