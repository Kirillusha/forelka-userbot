
import sys
from pyrogram.enums import ParseMode

async def term_cmd(client, message, args):
    pref = getattr(client, "prefix", ".")
    if not args:
        return await message.edit(
            f"<b>Terminal</b>\n"
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
    out = (stdout or b"").decode(errors="ignore")
    err = (stderr or b"").decode(errors="ignore")

    code = proc.returncode
    text = f"<b>$</b> <code>{cmd}</code>\n\n"

    if out:
        text += f"<b>stdout:</b>\n<blockquote expandable><code>{out}</code></blockquote>\n\n"
    if err:
        text += f"<b>stderr:</b>\n<blockquote expandable><code>{err}</code></blockquote>\n\n"

    text += f"<b>exit code:</b> <code>{code}</code>"

    if len(text) > 4000:
        text = text[:3990] + "</code>…"

    await message.edit(text, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["term"] = {"func": term_cmd, "module": module_name}
