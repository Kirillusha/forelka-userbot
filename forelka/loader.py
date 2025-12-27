import os
import importlib.util
import sys
import subprocess

class DependencyHandler:
    @staticmethod
    def get_reqs(path):
        if not path or not os.path.isfile(path):
            return []
        reqs = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if any(line.startswith(x) for x in ["# scope: pip: ", "# requirements: "]):
                        parts = line.split(":", 1)[1].strip().split()
                        reqs.extend(parts)
        except: pass
        return reqs

    @classmethod
    def install(cls, path):
        for req in cls.get_reqs(path):
            try:
                importlib.import_module(req)
            except ImportError:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", req, "--quiet"])
                except: pass

class ModuleLoader:
    def __init__(self, client):
        self.client = client

    def load(self, name, folder):
        path = os.path.abspath(os.path.join(folder, f"{name}.py"))
        if not os.path.exists(path):
            return False

        DependencyHandler.install(path)

        try:
            spec = importlib.util.spec_from_file_location(f"dynamic_mod_{name}", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                
                if hasattr(mod, "register"):
                    mod.register(self.client, self.client.commands, name)
                    self.client.loaded_modules.add(name)
                    self._fill_meta(name, mod)
                    return True
        except Exception as e:
            print(f"Failed to install {name}: {e}")
        return False

    def _fill_meta(self, name, mod):
        dev = getattr(mod, "__developer__", "Unknown")
        ver = getattr(mod, "__version__", "1.0")
        desc = getattr(mod, "__description__", "No description")

        self.client.meta_data[name] = {
            "developer": f"<emoji id=5771887475421090729>👤</emoji> <b>Dev:</b> <code>{dev}</code>",
            "version": f"<emoji id=5877468380125990242>➡️</emoji> <b>Ver:</b> <code>{ver}</code>",
            "description": f"<emoji id=5775887550262546277>❗️</emoji> <b>Info:</b> <i>{desc}</i>"
        }

    def load_all(self):
        self.client.meta_data = {}
        self.client.loaded_modules = set()
        for folder in ["modules", "loaded_modules"]:
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
                continue
            for file in os.listdir(folder):
                if file.endswith(".py") and not file.startswith("__"):
                    self.load(file[:-3].lower(), folder)

def load_all(client):
    ModuleLoader(client).load_all()

def load_module(client, name, folder):
    return ModuleLoader(client).load(name, folder)

def is_protected(name):
    return os.path.exists(os.path.join("modules", f"{name.lower()}.py"))
