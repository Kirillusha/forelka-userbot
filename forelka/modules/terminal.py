import sys
import asyncio
from pyrogram.enums import ParseMode

__forelka_meta__ = {
    "lib": "system",
    "name": "Terminal",
    "version": "1.0.0",
    "developer": "forelka",
    "description": "Выполнение команд в терминале из Telegram (опасно — используйте только овнерам).",
}

async def term_cmd(client, message, args):
    pref = getattr(client, "prefix", ".")
    if not args:
        return await message.edit(
            f"<emoji id=5877468380125990242>➡️</emoji> <b>Terminal</b>\n"
            f"<code>{pref}term &lt;command&gt;</code>",
            parse_mode=ParseMode.HTML
        )

    cmd = " ".join(args)

    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()
    out = (stdout or b"").decode(errors="ignore").strip()
    err = (stderr or b"").decode(errors="ignore").strip()

    text = f"<b>$</b> <code>{cmd}</code>\n\n"

    if out:
        text += f"<b>stdout:</b>\n<blockquote expandable><code>{out}</code></blockquote>\n\n"
    if err:
        text += f"<b>stderr:</b>\n<blockquote expandable><code>{err}</code></blockquote>\n\n"

    text += f"<b>exit code:</b> <code>{proc.returncode}</code>"

    if len(text) > 4000:
        cut = 4000 - len("</code></blockquote>")
        text = text[:cut] + "</code></blockquote>"

    await message.edit(text, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["term"] = {"func": term_cmd, "module": module_name, "description": "Выполнить команду в shell."}
