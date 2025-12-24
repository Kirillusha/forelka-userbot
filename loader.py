import importlib
import importlib.util
import os
import sys

MODULE_DIRS = ["modules", "loaded_modules"]

def load_module(app, module_name, folder):
    file_path = os.path.join(folder, f"{module_name}.py")
    if not os.path.exists(file_path):
        return False
    try:
        if module_name in sys.modules:
            module = importlib.reload(sys.modules[module_name])
        else:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

        if hasattr(module, "register"):
            module.register(app, app.commands, module_name)
            app.loaded_modules.add(module_name)
            return True
    except Exception:
        return False
    return False

def unload_module(app, module_name):
    cmds_to_del = [cmd for cmd, info in app.commands.items() if info.get("module") == module_name]
    for cmd in cmds_to_del:
        del app.commands[cmd]
    if module_name in sys.modules:
        del sys.modules[module_name]
    app.loaded_modules.discard(module_name)

def reload_module(app, module_name):
    folder = "modules"
    for d in MODULE_DIRS:
        if os.path.exists(os.path.join(d, f"{module_name}.py")):
            folder = d
            break
    unload_module(app, module_name)
    return load_module(app, module_name, folder)

def load_all_modules(app):
    for folder in MODULE_DIRS:
        if not os.path.exists(folder):
            os.makedirs(folder)
        for f in os.listdir(folder):
            if f.endswith(".py") and not f.startswith("_"):
                load_module(app, f[:-3], folder)
