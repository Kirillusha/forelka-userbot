# name: Ping
# version: 1.0.0
# developer: forelka
# description: Проверка задержки (ping/latency) юзербота.

import time
from pyrogram.enums import ParseMode

async def ping_cmd(client, message, args):
    start = time.perf_counter()
    await message.edit("<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Pinging...</b></blockquote>", parse_mode=ParseMode.HTML)
    
    ms = (time.perf_counter() - start) * 1000
    res = (
        f"<emoji id=5897962422169243693>👻</emoji> <b>Pong</b>\n"
        f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Latency:</b> <code>{ms:.2f} ms</code></blockquote>"
    )
    await message.edit(res, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["ping"] = {"func": ping_cmd, "module": module_name, "description": "Проверить задержку."}
