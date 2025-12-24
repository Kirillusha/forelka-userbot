import importlib
import importlib.util
import os
import sys

loaded_modules = {}

MODULE_DIRS = ["modules", "loaded_modules"]

def load_module(app, commands, module_name, folder="modules"):
    try:
        file_path = os.path.join(folder, f"{module_name}.py")
        if not os.path.exists(file_path):
            return False

        if module_name in loaded_modules:
            module = importlib.reload(loaded_modules[module_name])
        else:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

        if hasattr(module, "register"):
            module.register(app, commands, module_name)
            loaded_modules[module_name] = module
            return True
    except Exception as e:
        print(f"Error loading {module_name}: {e}")
    return False

def load_all_modules(app, commands):
    for folder in MODULE_DIRS:
        if not os.path.exists(folder):
            os.makedirs(folder)
            continue
        for f in os.listdir(folder):
            if f.endswith(".py") and not f.startswith("_"):
                module_name = f[:-3]
                load_module(app, commands, module_name, folder)

def unload_module(app, commands, module_name):
    to_remove = [cmd for cmd, info in commands.items() if info.get("module") == module_name]
    for cmd in to_remove:
        del commands[cmd]

    if module_name in loaded_modules:
        del loaded_modules[module_name]
    if module_name in sys.modules:
        del sys.modules[module_name]

def reload_module(app, commands, module_name, folder="modules"):
    unload_module(app, commands, module_name)
    return load_module(app, commands, module_name, folder)

def reload_all(app, commands):
    for module_name in list(loaded_modules.keys()):
        unload_module(app, commands, module_name)
    load_all_modules(app, commands)