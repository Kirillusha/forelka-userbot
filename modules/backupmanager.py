import os
import io
import sys
import zipfile
from forelka import loader

async def backup_cmd(client, message, args):
    await message.edit("<blockquote><emoji id=5891211339170326418>⏳</emoji> <b>Creating full backup...</b></blockquote>")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        mod_dir = "loaded_modules"
        if os.path.exists(mod_dir):
            for root, _, files in os.walk(mod_dir):
                for file in files:
                    if file.endswith(".py"):
                        zip_file.write(os.path.join(root, file), f"modules/{file}")
        for file in os.listdir("."):
            if file.endswith((".db", ".session", ".session-journal")):
                zip_file.write(file, f"database/{file}")
    zip_buffer.seek(0)
    zip_buffer.name = "forelka_full_backup.zip"
    topic_id = message.message_thread_id if message.message_thread_id else None
    await message.delete()
    await client.send_document(
        chat_id=message.chat.id,
        document=zip_buffer,
        caption="<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Full Backup complete!</b> (Mods + DB)</blockquote>",
        message_thread_id=topic_id
    )

async def restore_cmd(client, message, args):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Reply to a backup ZIP</b></blockquote>")
    await message.edit("<blockquote><emoji id=5891211339170326418>⏳</emoji> <b>Restoring everything...</b></blockquote>")
    try:
        zip_data = await client.download_media(message.reply_to_message, in_memory=True)
        zip_buffer = io.BytesIO(zip_data.getbuffer())
        with zipfile.ZipFile(zip_buffer, "r") as zip_ref:
            mod_files = [f for f in zip_ref.namelist() if f.startswith("modules/")]
            for f in mod_files:
                name = os.path.basename(f)
                with open(f"loaded_modules/{name}", "wb") as out:
                    out.write(zip_ref.read(f))
                loader.load_module(client, name[:-3], "loaded_modules")
            db_files = [f for f in zip_ref.namelist() if f.startswith("database/")]
            for f in db_files:
                name = os.path.basename(f)
                with open(name, "wb") as out:
                    out.write(zip_ref.read(f))
        await message.edit("<blockquote>✅ <b>Restore complete! Restarting...</b></blockquote>")
        os.execv(sys.executable, [sys.executable, "-m", "forelka"])
    except Exception as e:
        await message.edit(f"<blockquote>❌ <b>Error:</b> <code>{e}</code></blockquote>")

def register(app, commands, module_name):
    commands["backup"] = {"func": backup_cmd, "module": module_name}
    commands["restore"] = {"func": restore_cmd, "module": module_name}
