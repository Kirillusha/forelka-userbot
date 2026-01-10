from pyrogram.enums import ParseMode

__forelka_meta__ = {
    "lib": "system",
    "name": "Forelka Info",
    "version": "1.0.0",
    "developer": "forelka",
    "description": "Короткая информация о Forelka (ссылки/каналы/поддержка).",
}

async def ubinfo_cmd(client, message, args):
    text = (
        "Forelka Userbot\n\n"
        "Channel: @forelkauserbots\n"
        "Modules: @forelkausermodules\n"
        "Support: @forelka_support"
    )
    await message.edit(text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["forelka"] = {"func": ubinfo_cmd, "module": module_name, "description": "Показать ссылки/инфо о проекте."}
