import os
import importlib.util
import sys
import subprocess

def check_reqs(path):
    if not path or not os.path.isfile(path):
        return []
    reqs = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("# scope: pip: ") or line.startswith("# requirements: "):
                    parts = line.split(":", 1)[1].strip().split()
                    reqs.extend(parts)
    except: pass
    return reqs

def load_module(client, name, folder):
    path = os.path.abspath(os.path.join(folder, f"{name}.py"))
    if not os.path.exists(path):
        return False

    for req in check_reqs(path):
        try:
            importlib.import_module(req)
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", req])
            except: pass

    try:
        spec = importlib.util.spec_from_file_location(f"dynamic_mod_{name}", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "register"):
                mod.register(client, client.commands, name)
                client.loaded_modules.add(name)
                
                dev = getattr(mod, "__developer__", "Unknown")
                ver = getattr(mod, "__version__", "1.0")
                desc = getattr(mod, "__description__", "No description")
                
                client.meta_data[name] = {
                    "developer": f"<emoji id=5771887475421090729>👤</emoji> <b>Dev:</b> <code>{dev}</code>",
                    "version": f"<emoji id=5877468380125990242>➡️</emoji> <b>Ver:</b> <code>{ver}</code>",
                    "description": f"<emoji id=5775887550262546277>❗️</emoji> <b>Info:</b> <i>{desc}</i>"
                }
                return True
    except Exception as e:
        print(f"FAILED TO LOAD {name}: {e}")
    return False

def load_all(client):
    client.meta_data = {}
    client.loaded_modules = set()
    for folder in ["modules", "loaded_modules"]:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            continue
        for file in os.listdir(folder):
            if file.endswith(".py") and not file.startswith("__"):
                load_module(client, file[:-3].lower(), folder)

def is_protected(name):
    return os.path.exists(os.path.join("modules", f"{name.lower()}.py"))
