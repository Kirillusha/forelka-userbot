import importlib.util
import os
import sys
import inspect
import json
import requests

from pyrogram.enums import ParseMode

REPO_FILE = "repos.json"


def is_protected(name):
    return os.path.exists(f"modules/{name}.py") or name in ["loader", "main"]


def load_repos():
    if not os.path.exists(REPO_FILE):
        return []
    try:
        with open(REPO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except:
        pass
    return []


def save_repos(repos):
    try:
        with open(REPO_FILE, "w", encoding="utf-8") as f:
            json.dump(repos, f, ensure_ascii=False, indent=2)
    except:
        pass


def build_github_raw_url(repo_url, module_name):
    url = repo_url.rstrip("/")
    if "github.com" not in url:
        return None
    if "raw.githubusercontent.com" in url:
        base = url
    else:
        if url.endswith(".git"):
            url = url[:-4]
        parts = url.split("github.com/")[-1].split("/")
        if len(parts) < 2:
            return None
        owner, repo = parts[0], parts[1]
        branch = "main"
        path = ""
        if len(parts) > 2:
            path = "/".join(parts[2:])
        base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
        if path:
            base += f"/{path.strip('/')}"
    return f"{base.rstrip('/')}/{module_name}.py"


def find_in_repos(module_name):
    repos = load_repos()
    for repo in repos:
        raw_url = build_github_raw_url(repo, module_name)
        if not raw_url:
            continue
        try:
            r = requests.get(raw_url, timeout=10)
            if r.ok and r.content:
                return raw_url, r.content
        except:
            continue
    return None, None


async def dlm_cmd(client, message, args):
    if not args:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> "
            "<b>Usage:</b> <code>.dlm [url|name]</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    target = args[0]

    if target.startswith("http://") or target.startswith("https://"):
        url = target
        base_name = os.path.basename(url.split("?")[0])
        if base_name.endswith(".py"):
            name = base_name[:-3].lower()
        else:
            name = base_name.lower() or "module"
        if is_protected(name):
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>",
                parse_mode=ParseMode.HTML,
            )
        path = f"loaded_modules/{name}.py"
        await message.edit(
            f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Downloading {name}...</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)

            if load_module(client, name, "loaded_modules"):
                await message.edit(
                    f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} installed</b></blockquote>",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await message.edit(
                    "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>",
                    parse_mode=ParseMode.HTML,
                )
        except Exception as e:
            await message.edit(
                f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>",
                parse_mode=ParseMode.HTML,
            )
        return

    name = target.lower()
    if is_protected(name):
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    await message.edit(
        f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Searching {name} in repos...</b></blockquote>",
        parse_mode=ParseMode.HTML,
    )

    url, content = find_in_repos(name)
    if not content:
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Module not found in GitHub repos</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    path = f"loaded_modules/{name}.py"
    try:
        with open(path, "wb") as f:
            f.write(content)

        if load_module(client, name, "loaded_modules"):
            await message.edit(
                f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} installed</b>\n"
                f"<code>{url}</code></blockquote>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>",
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )


async def lm_cmd(client, message, args):
    if not message.reply_to_message or not message.reply_to_message.document:
        out = (
            "<blockquote><b>Modules:</b>\n"
            + "\n".join([f" • <code>{m}</code>" for m in sorted(client.loaded_modules)])
            + "</blockquote>"
        )
        return await message.edit(out, parse_mode=ParseMode.HTML)

    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".py"):
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>.py only</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    name = (args[0] if args else doc.file_name[:-3]).lower()
    if is_protected(name):
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    path = f"loaded_modules/{name}.py"
    await message.edit(
        f"<blockquote><emoji id=5899757765743615694>⬇️</emoji> <b>Saving {name}...</b></blockquote>",
        parse_mode=ParseMode.HTML,
    )

    try:
        await client.download_media(message.reply_to_message, file_name=path)
        if load_module(client, name, "loaded_modules"):
            await message.edit(
                f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} loaded</b></blockquote>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>",
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )


async def ulm_cmd(client, message, args):
    if not args:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ulm [name]</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    name = args[0].lower()
    if is_protected(name):
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    path = f"loaded_modules/{name}.py"
    if os.path.exists(path):
        unload_module(client, name)
        os.remove(path)
        await message.edit(
            f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} deleted</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )


async def ml_cmd(client, message, args):
    if not args:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ml [name]</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    name = args[0]
    path = f"loaded_modules/{name}.py"
    if not os.path.exists(path):
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    await message.delete()
    await client.send_document(
        message.chat.id,
        path,
        caption=(
            f"<blockquote><emoji id=5776375003280838798>✅</emoji> "
            f"<b>Module:</b> <code>{name}</code></blockquote>"
        ),
        parse_mode=ParseMode.HTML,
    )


async def addrepo_cmd(client, message, args):
    if not args:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> "
            "<b>Usage:</b> <code>.addrepo [github-url]</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    url = args[0].strip()
    if not (url.startswith("http://") or url.startswith("https://")) or "github.com" not in url:
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>GitHub url only</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    repos = load_repos()
    if url in repos:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Already added</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    repos.append(url)
    save_repos(repos)
    await message.edit(
        f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Repo added:</b> <code>{url}</code></blockquote>",
        parse_mode=ParseMode.HTML,
    )


async def delrepo_cmd(client, message, args):
    if not args:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> "
            "<b>Usage:</b> <code>.delrepo [url|index]</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    repos = load_repos()
    if not repos:
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>No repos</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    arg = args[0].strip()
    removed = None

    if arg.isdigit():
        idx = int(arg) - 1
        if 0 <= idx < len(repos):
            removed = repos.pop(idx)
    else:
        if arg in repos:
            repos.remove(arg)
            removed = arg

    if not removed:
        return await message.edit(
            "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Repo not found</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    save_repos(repos)
    await message.edit(
        f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Repo removed:</b> <code>{removed}</code></blockquote>",
        parse_mode=ParseMode.HTML,
    )


async def repos_cmd(client, message, args):
    repos = load_repos()
    if not repos:
        return await message.edit(
            "<blockquote><b>Repos:</b>\n<code>no repos</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    lines = []
    for i, r in enumerate(repos, 1):
        lines.append(f"{i}. <code>{r}</code>")

    out = "<blockquote><b>Repos:</b>\n" + "\n".join(lines) + "</blockquote>"
    await message.edit(out, parse_mode=ParseMode.HTML)


def load_module(app, name, folder):
    path = os.path.abspath(os.path.join(folder, f"{name}.py"))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)

        reg = getattr(mod, "register", None)
        if reg:
            sig = inspect.signature(reg)
            if len(sig.parameters) == 3:
                reg(app, app.commands, name)
            else:
                reg(app, app.commands)
            app.loaded_modules.add(name)
            return True
    except:
        return False
    return False


def unload_module(app, name):
    to_pop = [k for k, v in list(app.commands.items()) if v.get("module") == name]
    for k in to_pop:
        app.commands.pop(k)
    app.loaded_modules.discard(name)
    if name in sys.modules:
        del sys.modules[name]


def load_all(app):
    app.commands.update(
        {
            "dlm": {"func": dlm_cmd, "module": "loader"},
            "lm": {"func": lm_cmd, "module": "loader"},
            "ulm": {"func": ulm_cmd, "module": "loader"},
            "ml": {"func": ml_cmd, "module": "loader"},
            "addrepo": {"func": addrepo_cmd, "module": "loader"},
            "delrepo": {"func": delrepo_cmd, "module": "loader"},
            "repos": {"func": repos_cmd, "module": "loader"},
        }
    )
    app.loaded_modules.add("loader")

    for d in ["modules", "loaded_modules"]:
        if not os.path.exists(d):
            os.makedirs(d)
        for f in sorted(os.listdir(d)):
            if f.endswith(".py") and not f.startswith("_"):
                load_module(app, f[:-3], d)
