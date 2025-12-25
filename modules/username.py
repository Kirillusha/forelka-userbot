from pyrogram.enums import ParseMode

async def username_cmd(client, message, args):
    me = await client.get_me()
    
    usernames_list = []
    
    if me.usernames:
        for u in me.usernames:
            nft_label = " [NFT]" if not u.is_editable else ""
            active_label = " <emoji id=5776375003280838798>✅</emoji>" if u.is_active else " <emoji id=5778527486270770928>❌</emoji>"
            usernames_list.append(f"@{u.username}{nft_label}{active_label}")
    elif me.username:
        usernames_list.append(f"@{me.username} <emoji id=5776375003280838798>✅</emoji>")
    else:
        usernames_list.append("<code>None</code>")

    res = (
        f"<emoji id=5897962422169243693>👻</emoji> <b>Usernames Info</b>\n"
        f"<blockquote>" + "\n".join(usernames_list) + "</blockquote>"
    )
    
    await message.edit(res, parse_mode=ParseMode.HTML)

def register(app, commands, module_name):
    commands["username"] = {"func": username_cmd, "module": module_name}
    commands["un"] = {"func": username_cmd, "module": module_name}
