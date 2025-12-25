import os
import io
import zipfile
from loader import load_module 

async def backupmods_cmd(client, message, args):
    """Backup all loaded modules to ZIP"""
    target_dir = "loaded_modules"
    
    if not os.path.exists(target_dir) or not os.listdir(target_dir):
        return await message.edit("<blockquote><emoji id=5210952531676504517>❌</emoji> <b>Folder empty</b></blockquote>")
    
    await message.edit("<blockquote><emoji id=5891211339170326418>⏳</emoji> <b>Creating backup...</b></blockquote>")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".py"):
                    zip_file.write(os.path.join(root, file), file)
    
    zip_buffer.seek(0)
    zip_buffer.name = "modules_backup.zip"
    
    topic_id = message.message_thread_id if message.message_thread_id else None
    
    await message.delete()
    await client.send_document(
        chat_id=message.chat.id,
        document=zip_buffer,
        caption="<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Backup complete!</b></blockquote>",
        message_thread_id=topic_id
    )

async def restoremods_cmd(client, message, args):
    """Restore modules from ZIP (reply)"""
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Reply to a ZIP backup</b></blockquote>")
    
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".zip"):
        return await message.edit("<blockquote><emoji id=5210952531676504517>❌</emoji> <b>Not a ZIP</b></blockquote>")
    
    await message.edit("<blockquote><emoji id=5891211339170326418>⏳</emoji> <b>Restoring...</b></blockquote>")
    
    try:
        zip_data = await client.download_media(message.reply_to_message, in_memory=True)
        zip_buffer = io.BytesIO(zip_data.getbuffer())
        
        target_dir = "loaded_modules"
        if not os.path.exists(target_dir): os.makedirs(target_dir)
        
        with zipfile.ZipFile(zip_buffer, "r") as zip_ref:
            py_files = [f for f in zip_ref.namelist() if f.endswith(".py")]
            zip_ref.extractall(target_dir, members=py_files)
            
            for file in py_files:
                load_module(client, file[:-3], target_dir)
        
        stk = "<emoji id=5877540355187937244>📤</emoji>"
        await message.edit(f"<blockquote>{stk} <b>Restored {len(py_files)} modules!</b></blockquote>")
    except Exception as e:
        await message.edit(f"<blockquote><emoji id=5210952531676504517>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>")

def register(app, commands, module_name):
    commands["backupmods"] = {"func": backupmods_cmd, "module": module_name}
    commands["restoremods"] = {"func": restoremods_cmd, "module": module_name}
