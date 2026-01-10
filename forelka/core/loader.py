import importlib.util
import importlib.metadata
import os
import sys
import inspect
import ast
import subprocess
import html
import requests

from pyrogram.enums import ParseMode

from .meta import normalize_module_meta

BASE_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
SYSTEM_MODULES_DIR = os.path.join(PACKAGE_DIR, "modules")

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


def _extract_forelka_meta_literal(py_path: str):
    """
    Пытаемся достать __forelka_meta__ как literal dict НЕ выполняя модуль.
    Нужен для авто-установки зависимостей до import внутри модуля.
    """
    try:
        with open(py_path, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename=py_path)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == "__forelka_meta__":
                        return ast.literal_eval(node.value)
    except Exception:
        return None
    return None


def _extract_forelka_meta_header(py_path: str):
    """
    Достаём мету из комментариев в начале файла (как ты просил: "под #").

    Пример:
    # name: TicTacToe
    # version: 2.0.0
    # developer: @hikarimods
    # description: Играй в крестики-нолики
    # pip: aiohttp, pillow
    """
    out = {}
    try:
        with open(py_path, "r", encoding="utf-8") as f:
            for _ in range(40):
                line = f.readline()
                if not line:
                    break
                s = line.strip()
                if not s:
                    continue
                if not s.startswith("#"):
                    break
                s = s.lstrip("#").strip()
                if not s:
                    continue
                if ":" in s:
                    k, v = s.split(":", 1)
                elif "=" in s:
                    k, v = s.split("=", 1)
                else:
                    continue
                k = k.strip().lower()
                v = v.strip()
                if not v:
                    continue
                # русские алиасы
                if k in ("название", "имя"):
                    k = "name"
                elif k in ("версия",):
                    k = "version"
                elif k in ("разработчик", "автор"):
                    k = "developer"
                elif k in ("описание",):
                    k = "description"
                out[k] = v
    except Exception:
        return None
    return out or None


def _extract_forelka_meta_pre(py_path: str):
    # header + __forelka_meta__ (dict имеет приоритет)
    header = _extract_forelka_meta_header(py_path) or {}
    literal = _extract_forelka_meta_literal(py_path) or {}
    merged = dict(header)
    if isinstance(literal, dict):
        merged.update(literal)
    return merged or None


def _is_truthy_env(name: str, default: str = "1") -> bool:
    v = os.environ.get(name, default).strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _ensure_pip_packages(packages):
    """
    Устанавливает pip-пакеты (если включено) перед загрузкой модуля.
    По умолчанию включено, выключить: FORELKA_AUTO_PIP=0
    """
    if not packages:
        return
    if not _is_truthy_env("FORELKA_AUTO_PIP", "1"):
        return

    # Ограничим “размер аппетита” модуля
    packages = [p for p in packages if isinstance(p, str) and p.strip()]
    packages = [p.strip() for p in packages][:20]
    if not packages:
        return

    # Пробуем не дёргать pip, если дистрибутив уже установлен
    missing = []
    for p in packages:
        dist = p.split("==", 1)[0].split(">=", 1)[0].split("<=", 1)[0].strip()
        if not dist:
            continue
        try:
            importlib.metadata.version(dist)
        except Exception:
            missing.append(p)

    if not missing:
        return

    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", *missing]
    subprocess.run(cmd, check=False, timeout=600)


def _escape(s) -> str:
    try:
        return html.escape(str(s), quote=True)
    except Exception:
        return ""


def _render_module_card(app, module_name: str, *, action: str) -> str:
    meta = None
    try:
        meta = (getattr(app, "modules_meta", {}) or {}).get(module_name)
    except Exception:
        meta = None

    if not meta:
        meta = normalize_module_meta(module_name, None, default_lib="external")

    title = _escape(getattr(meta, "name", module_name) or module_name)
    ver = _escape(getattr(meta, "version", "0.0.0") or "0.0.0")
    desc = _escape(getattr(meta, "description", "") or "")
    dev = _escape(getattr(meta, "developer", "unknown") or "unknown")
    pref = _escape(getattr(app, "prefix", ".") or ".")

    # команды модуля
    cmds = []
    try:
        for cmd_name, info in (getattr(app, "commands", {}) or {}).items():
            if (info or {}).get("module") != module_name:
                continue
            cmd_desc = (info or {}).get("description") or (info or {}).get("desc") or ""
            cmd_desc = _escape(cmd_desc)
            cmds.append((str(cmd_name), cmd_desc))
    except Exception:
        cmds = []

    cmds.sort(key=lambda x: x[0])
    cmd_lines = []
    for i, (c, d) in enumerate(cmds[:18], start=1):
        tail = f" {d}" if d else ""
        cmd_lines.append(f"▫️ <code>{pref}{_escape(c)}</code>{tail}")
    if len(cmds) > 18:
        cmd_lines.append(f"… и ещё <code>{len(cmds) - 18}</code> команд(ы)")

    cmd_block = "\n".join(cmd_lines) if cmd_lines else "<i>Команды не зарегистрированы</i>"

    desc_line = f"<blockquote>ℹ️ {desc}</blockquote>\n\n" if desc else ""
    dev_line = f"\n<blockquote>⭐️ Этот модуль сделан <code>{dev}</code>.</blockquote>" if dev else ""

    return (
        f"🪐 <b>Модуль {title}</b> (v{ver}) {_escape(action)} (΄◞ิ౪◟ิ‵)\n"
        f"{desc_line}"
        f"<blockquote expandable>\n{cmd_block}\n</blockquote>"
        f"{dev_line}"
    )


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
            await message.edit(_render_module_card(client, name, action="установлен и загружен"), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
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
            await message.edit(_render_module_card(client, name, action="загружен"), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
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
        # Достаём мету ДО выполнения кода, чтобы поставить зависимости
        raw_meta_pre = _extract_forelka_meta_pre(path)

        default_lib = "external"
        try:
            folder_abs = os.path.abspath(folder)
            if folder_abs == os.path.abspath(SYSTEM_MODULES_DIR):
                default_lib = "system"
            elif folder_abs == os.path.abspath(_legacy_modules_dir()):
                default_lib = "legacy"
        except Exception:
            pass

        try:
            meta_pre = normalize_module_meta(name, raw_meta_pre, default_lib=default_lib)
            _ensure_pip_packages(meta_pre.pip)
        except Exception:
            pass

        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)

        # --- module meta ---
        try:
            raw_meta = getattr(mod, "__forelka_meta__", None)
        except Exception:
            raw_meta = None

        try:
            if not hasattr(app, "modules_meta") or not isinstance(getattr(app, "modules_meta"), dict):
                app.modules_meta = {}
            app.modules_meta[name] = normalize_module_meta(name, raw_meta, default_lib=default_lib)
        except Exception:
            pass
        
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
    if not hasattr(app, "modules_meta") or not isinstance(getattr(app, "modules_meta"), dict):
        app.modules_meta = {}

    app.commands.update({
        "dlm": {"func": dlm_cmd, "module": "loader", "description": "Скачать и установить модуль по URL."},
        "lm":  {"func": lm_cmd,  "module": "loader", "description": "Загрузить модуль из .py файла (reply) или показать список."},
        "ulm": {"func": ulm_cmd, "module": "loader", "description": "Удалить установленный модуль из loaded_modules."},
        "ml":  {"func": ml_cmd,  "module": "loader", "description": "Отправить файл установленного модуля."}
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
