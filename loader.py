import importlib
import importlib.util
import os
import sys
import inspect

MODULE_DIRS = ["modules", "loaded_modules"]

async def help_cmd(client, message, args):
    text = (
        f"**Forelka UB**\n"
        f"**Modules:** `{len(client.loaded_modules)}`\n"
        f"**Commands:** `{len(client.commands)}`\n\n"
        f"**List:**\n`" + "`, `".join(sorted(client.commands.keys())) + "`"
    )
    await message.edit(text)

async def reload_cmd(client, message, args):
    if not args:
        reload_all(client)
        await message.edit("`All modules reloaded`")
    else:
        module_name = args[0]
        if reload_module(client, module_name):
            await message.edit(f"`Module {module_name} reloaded`")
        else:
            await message.edit(f"`Module {module_name} not found`")

def register_system(app):
    app.commands["help"] = {"func": help_cmd, "desc": "System help", "module": "system"}
    app.commands["reload"] = {"func": reload_cmd, "desc": "Reload logic", "module": "system"}
    app.loaded_modules.add("system")

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
            sig = inspect.signature(module.register)
            params = len(sig.parameters)
            if params == 3:
                module.register(app, app.commands, module_name)
            elif params == 2:
                module.register(app, app.commands)
            else:
                module.register(app)
            app.loaded_modules.add(module_name)
            return True
    except Exception:
        return False
    return False

def unload_module(app, module_name):
    to_del = [cmd for cmd, info in app.commands.items() if info.get("module") == module_name]
    for cmd in to_del:
        del app.commands[cmd]
    if module_name in sys.modules:
        del sys.modules[module_name]
    app.loaded_modules.discard(module_name)

def reload_module(app, module_name):
    if module_name == "system":
        register_system(app)
        return True
    folder = next((d for d in MODULE_DIRS if os.path.exists(os.path.join(d, f"{module_name}.py"))), "modules")
    unload_module(app, module_name)
    return load_module(app, module_name, folder)

def load_all_modules(app):
    register_system(app)
    for folder in MODULE_DIRS:
        if not os.path.exists(folder):
            os.makedirs(folder)
        for f in os.listdir(folder):
            if f.endswith(".py") and not f.startswith("_"):
                load_module(app, f[:-3], folder)

def reload_all(app):
    current = list(app.loaded_modules)
    for m in current:
        if m != "system":
            unload_module(app, m)
    load_all_modules(app)
