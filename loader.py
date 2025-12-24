import importlib
import importlib.util
import os
import sys
import inspect
import requests

MODULE_DIRS = ["modules", "loaded_modules"]

async def dlm_cmd(client, message, args):
    if len(args) < 2: 
        return await message.edit(".dlm <url> <name>")
    
    url, name = args[0], args[1]
    path = f"loaded_modules/{name}.py"
    try:
        r = requests.get(url)
        with open(path, "wb") as f: 
            f.write(r.content)
        if load_module(client, name, "loaded_modules"):
            await message.edit(f"Loaded: {name}")
        else:
            await message.edit(f"Error loading: {name}")
    except Exception as e: 
        await message.edit(f"Error: {e}")

async def ulm_cmd(client, message, args):
    if not args: 
        return await message.edit(".ulm <name>")
    
    name, unloaded = args[0], False
    for d in MODULE_DIRS:
        path = f"{d}/{name}.py"
        if os.path.exists(path):
            unload_module(client, name)
            os.remove(path)
            unloaded = True
            break
    await message.edit("Deleted" if unloaded else "Not found")

def load_module(app, name, folder):
    path = os.path.join(folder, f"{name}.py")
    if not os.path.exists(path): return False
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        if name in sys.modules: 
            mod = importlib.reload(sys.modules[name])
        else:
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
        if hasattr(mod, "register"):
            sig = inspect.signature(mod.register)
            if len(sig.parameters) == 3: 
                mod.register(app, app.commands, name)
            else: 
                mod.register(app, app.commands)
            app.loaded_modules.add(name)
            return True
    except Exception: 
        return False

def unload_module(app, name):
    [app.commands.pop(k) for k in [k for k, v in app.commands.items() if v.get("module") == name]]
    app.loaded_modules.discard(name)
    if name in sys.modules: 
        del sys.modules[name]

def load_all(app):
    app.commands["dlm"] = {"func": dlm_cmd, "module": "loader"}
    app.commands["ulm"] = {"func": ulm_cmd, "module": "loader"}
    app.loaded_modules.add("loader")
    for d in MODULE_DIRS:
        if not os.path.exists(d): 
            os.makedirs(d)
        for f in os.listdir(d):
            if f.endswith(".py") and not f.startswith("_"):
                load_module(app, f[:-3], d)
