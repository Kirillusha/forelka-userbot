import os
import importlib

class ModuleLoader:
    def __init__(self, app, commands, prefix):
        self.app = app
        self.commands = commands
        self.prefix = prefix

    def load_modules(self):
        modules_folder = "modules"
        for filename in os.listdir(modules_folder):
            if filename.endswith(".py") and filename not in ("__init__.py", "loader.py"):
                modulename = filename[:-3]
                module = importlib.import_module(f"{modules_folder}.{modulename}")
                if hasattr(module, "register"):
                    module.register(self.app, self.commands, self.prefix, modulename)
                print(f"Модуль {modulename} загружен")