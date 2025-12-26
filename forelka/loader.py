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
    except:
        pass
    return reqs

def load_module(client, name, folder, warnings=None, reqs_list=None):
    path = os.path.abspath(os.path.join(folder, f"{name}.py"))
    if not os.path.exists(path):
        return False

    reqs = check_reqs(path)
    for req in reqs:
        try:
            importlib.import_module(req)
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", req])
                if reqs_list is not None:
                    reqs_list.append(req)
            except:
                pass

    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            return False
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "register"):
            mod.register(client, client.commands, name)
            client.loaded_modules.add(name)
            client.meta_data[name] = {
                "developer": getattr(mod, "__developer__", "Unknown"),
                "version": getattr(mod, "__version__", "1.0"),
                "description": getattr(mod, "__description__", "No description")
            }
            return True
    except Exception as e:
        print(f"Error loading {name}: {e}")
        return False
    return False

def load_all(client):
    if not hasattr(client, "meta_data"):
        client.meta_data = {}
    if not os.path.exists("loaded_modules"):
        os.makedirs("loaded_modules")
    for folder in ["modules", "loaded_modules"]:
        if not os.path.exists(folder): continue
        for file in os.listdir(folder):
            if file.endswith(".py") and not file.startswith("__"):
                load_module(client, file[:-3].lower(), folder)

def is_protected(name):
    return os.path.exists(f"modules/{name.lower()}.py")
