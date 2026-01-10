from pyrogram.enums import ParseMode


__forelka_meta__ = {
    "lib": "system",
    "developer": "forelka",
    "description": "Показ метаданных модулей (lib/developer/description).",
}


def _format_meta(name: str, meta) -> str:
    lib = getattr(meta, "lib", "unknown")
    dev = getattr(meta, "developer", "unknown")
    desc = getattr(meta, "description", "")
    desc_line = f"\n<b>Description:</b> {desc}" if desc else ""
    return (
        "<blockquote>"
        f"<b>Module:</b> <code>{name}</code>\n"
        f"<b>Lib:</b> <code>{lib}</code>\n"
        f"<b>Developer:</b> <code>{dev}</code>"
        f"{desc_line}"
        "</blockquote>"
    )


async def minfo_cmd(client, message, args):
    mods = getattr(client, "modules_meta", {}) or {}
    if not args:
        if not mods:
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>No module meta</b></blockquote>",
                parse_mode=ParseMode.HTML,
            )

        # Короткий список всех модулей
        lines = []
        for name in sorted(mods.keys()):
            meta = mods.get(name)
            dev = getattr(meta, "developer", "unknown")
            desc = getattr(meta, "description", "")
            short = (desc[:80] + "...") if len(desc) > 80 else desc
            extra = f" — {short}" if short else ""
            lines.append(f"• <code>{name}</code> (<code>{dev}</code>){extra}")

        text = (
            "<emoji id=5897962422169243693>👻</emoji> <b>Module meta</b>\n"
            "<blockquote>"
            "<b>Usage:</b> <code>.minfo &lt;module&gt;</code>\n"
            "</blockquote>\n\n"
            "<blockquote expandable>"
            + "\n".join(lines)
            + "</blockquote>"
        )
        return await message.edit(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    name = args[0].lower().strip()
    meta = mods.get(name)
    if not meta:
        return await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Unknown module:</b> <code>{name}</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    text = "<emoji id=5897962422169243693>👻</emoji> <b>Module meta</b>\n\n" + _format_meta(name, meta)
    await message.edit(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def register(app, commands, module_name):
    commands["minfo"] = {"func": minfo_cmd, "module": module_name}

