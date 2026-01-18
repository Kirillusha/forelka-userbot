import os
import json
from pyrogram.enums import ParseMode


def _load_config(client):
    config_path = f"config-{client.me.id}.json"
    config = {"prefix": "."}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass
    return config

async def log_cmd(client, message, args):
    log_file = "forelka.log"
    if not os.path.exists(log_file):
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Log file not found</b></blockquote>", parse_mode=ParseMode.HTML)

    await message.edit("<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Sending logs...</b></blockquote>", parse_mode=ParseMode.HTML)
    config = _load_config(client)
    chat_id = config.get("log_group_id") or "me"
    thread_id = config.get("log_topic_logs_id")
    try:
        await client.send_document(
            chat_id,
            log_file,
            caption="<emoji id=5897962422169243693>👻</emoji> <b>Forelka Logs</b>",
            message_thread_id=thread_id,
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await client.send_document(
            chat_id,
            log_file,
            caption="<emoji id=5897962422169243693>👻</emoji> <b>Forelka Logs</b>",
            parse_mode=ParseMode.HTML,
        )
    destination = "Log group" if config.get("log_group_id") else "Saved Messages"
    await message.edit(
        f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Logs sent to {destination}</b></blockquote>",
        parse_mode=ParseMode.HTML,
    )

def register(app, commands, module_name):
    commands["log"] = {"func": log_cmd, "module": module_name}
