from pyrogram.enums import ParseMode


async def setlang_cmd(client, message, args):
    pref = getattr(client, "prefix", ".")
    t = getattr(client, "t", lambda k, default=None, **kw: default or k)

    # Показать список языков
    if not args:
        current = getattr(client, "lang", "ru")
        langs = []
        try:
            langs = list(getattr(client, "available_languages", lambda: [])())
        except Exception:
            langs = []
        langs_str = ", ".join(langs) if langs else "ru"

        text = (
            f"<emoji id=5897962422169243693>👻</emoji> <b>{t('setlang.title', default='Language')}</b>\n\n"
            f"<blockquote><b>{t('setlang.current', default='Current language:')}</b> <code>{current}</code>\n"
            f"<b>{t('setlang.available', default='Available:')}</b> <code>{langs_str}</code>\n\n"
            f"<emoji id=5775887550262546277>❗️</emoji> <b>{t('setlang.usage', default='Usage: {prefix}setlang [code]', prefix=pref)}</b></blockquote>"
        )
        return await message.edit(text, parse_mode=ParseMode.HTML)

    # Установить язык
    code = (args[0] or "").lower().strip()
    ok = False
    try:
        ok = bool(getattr(client, "set_lang")(code))
    except Exception:
        ok = False

    if not ok:
        return await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>{t('setlang.not_found', default='Language not found: {code}', code=code)}</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    return await message.edit(
        f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>{t('setlang.changed', default='Language set to: {code}', code=code)}</b></blockquote>",
        parse_mode=ParseMode.HTML,
    )


def register(app, commands, module_name):
    commands["setlang"] = {"func": setlang_cmd, "module": module_name}
