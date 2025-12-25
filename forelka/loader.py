import importlib.util
import os
import sys
import subprocess
import traceback

def is_protected(name):
    return name in ["loader", "main", "owners", "alias"] or os.path.exists(f"modules/{name}.py")

def check_reqs(path):
    installed = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for line in content.splitlines():
        if line.strip().startswith(("# requirements:", "# req:")):
            libs = line.split(":", 1)[1].strip().split()
            for lib in libs:
                try: 
                    subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
                    installed.append(lib)
                except: pass
    return installed

def get_full_meta(path):
    meta = {"developer": "Unknown", "description": "No description provided.", "version": "1.0"}
    if not os.path.exists(path): return meta
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("# meta"):
                parts = line.replace("# meta", "").strip().split(":", 1)
                if len(parts) == 2:
                    meta[parts[0].strip().lower()] = parts[1].strip()
    return meta

def load_module(app, name, folder, warnings=None, reqs_out=None):
    path = os.path.abspath(os.path.join(folder, f"{name}.py"))
    try:
        reqs = check_reqs(path)
        if reqs_out is not None: reqs_out.extend(reqs)
        if name in sys.modules: del sys.modules[name]
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        reg = getattr(mod, "register", None)
        if reg:
            temp_commands = {}
            reg(app, temp_commands, name)
            for cmd_name, cmd_data in temp_commands.items():
                app.commands[cmd_name] = cmd_data
            if not hasattr(app, "meta_data"): app.meta_data = {}
            app.meta_data[name] = get_full_meta(path)
            app.loaded_modules.add(name)
            return True
    except: print(traceback.format_exc())
    return False

def load_all(app):
    for folder in ["modules", "loaded_modules"]:
        if not os.path.exists(folder): os.makedirs(folder)
        for file in os.listdir(folder):
            if file.endswith(".py") and file != "__init__.py":
                load_module(app, file[:-3], folder)
