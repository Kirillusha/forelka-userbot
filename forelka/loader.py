import importlib.util
import os
import sys
import inspect
import requests

from pyrogram.enums import ParseMode

BASE_DIR = os.path.dirname(__file__)
SYSTEM_MODULES_DIR = os.path.join(BASE_DIR, "modules")

# Backward compatibility: раньше ядро импортировалось как `import loader`
# и модули использовали строку "loader" в `info["module"]`.
sys.modules.setdefault("loader", sys.modules[__name__])


def _legacy_modules_dir() -> str:
    # На случай, если пользователь хранит модули в корне проекта (старый формат).
    return os.path.abspath("modules")


def _external_modules_dir() -> str:
    # Загруженные/скачанные модули всегда живут в рабочей папке.
    return os.path.abspath("loaded_modules")


def _is_system_module(name: str) -> bool:
    return os.path.exists(os.path.join(SYSTEM_MODULES_DIR, f"{name}.py"))


def _is_legacy_module(name: str) -> bool:
    return os.path.exists(os.path.join(_legacy_modules_dir(), f"{name}.py"))


def is_protected(name):
    # Запрещаем ставить модуль с именем системного/точки входа
    return _is_system_module(name) or _is_legacy_module(name) or name in ["loader", "main"]

async def dlm_cmd(client, message, args):
    if len(args) < 2: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .dlm [url] [name]</b></blockquote>", parse_mode=ParseMode.HTML)
    
    url, name = args[0], args[1].lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    path = f"loaded_modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Downloading {name}...</b></blockquote>", parse_mode=ParseMode.HTML)
    
    try:
        r = requests.get(url, timeout=10)
        with open(path, "wb") as f: 
            f.write(r.content)
            
        if load_module(client, name, "loaded_modules"):
            await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} installed</b></blockquote>", parse_mode=ParseMode.HTML)
        else: 
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: 
        await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>", parse_mode=ParseMode.HTML)

async def lm_cmd(client, message, args):
    if not message.reply_to_message or not message.reply_to_message.document:
        out = "<blockquote><b>Modules:</b>\n" + "\n".join([f" • <code>{m}</code>" for m in sorted(client.loaded_modules)]) + "</blockquote>"
        return await message.edit(out, parse_mode=ParseMode.HTML)
    
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".py"): 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>.py only</b></blockquote>", parse_mode=ParseMode.HTML)
    
    name = (args[0] if args else doc.file_name[:-3]).lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    path = f"loaded_modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5899757765743615694>⬇️</emoji> <b>Saving {name}...</b></blockquote>", parse_mode=ParseMode.HTML)
    
    try:
        await client.download_media(message.reply_to_message, file_name=path)
        if load_module(client, name, "loaded_modules"): 
            await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} loaded</b></blockquote>", parse_mode=ParseMode.HTML)
        else: 
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: 
        await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>", parse_mode=ParseMode.HTML)

async def ulm_cmd(client, message, args):
    if not args: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ulm [name]</b></blockquote>", parse_mode=ParseMode.HTML)
    
    name = args[0].lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    path = f"loaded_modules/{name}.py"
    if os.path.exists(path):
        unload_module(client, name)
        os.remove(path)
        await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} deleted</b></blockquote>", parse_mode=ParseMode.HTML)
    else: 
        await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>", parse_mode=ParseMode.HTML)

async def ml_cmd(client, message, args):
    if not args: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ml [name]</b></blockquote>", parse_mode=ParseMode.HTML)
    
    name = args[0]
    path = f"loaded_modules/{name}.py"
    if not os.path.exists(path): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>", parse_mode=ParseMode.HTML)
    
    await message.delete()
    await client.send_document(
        message.chat.id, 
        path, 
        caption=f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module:</b> <code>{name}</code></blockquote>", 
        parse_mode=ParseMode.HTML
    )

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
    app.commands.update({
        "dlm": {"func": dlm_cmd, "module": "loader"},
        "lm":  {"func": lm_cmd,  "module": "loader"},
        "ulm": {"func": ulm_cmd, "module": "loader"},
        "ml":  {"func": ml_cmd,  "module": "loader"}
    })
    app.loaded_modules.add("loader")
    
    module_dirs = []
    module_dirs.append(SYSTEM_MODULES_DIR)

    legacy = _legacy_modules_dir()
    if legacy != SYSTEM_MODULES_DIR and os.path.exists(legacy):
        module_dirs.append(legacy)

    external = _external_modules_dir()
    if not os.path.exists(external):
        os.makedirs(external)
    module_dirs.append(external)

    for d in module_dirs:
        if not os.path.exists(d):
            os.makedirs(d)
        ignore = {"__init__.py"}
        # Не загружаем forelka/modules/loader.py (устаревший класс ModuleLoader),
        # чтобы не перезатереть sys.modules["loader"] (ядро).
        if d in (SYSTEM_MODULES_DIR, legacy):
            ignore.add("loader.py")

        for f in sorted(os.listdir(d)):
            if f in ignore:
                continue
            if f.endswith(".py") and not f.startswith("_"):
                load_module(app, f[:-3], d)
