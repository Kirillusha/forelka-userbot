import importlib
import importlib.util
import os
import sys

loaded_modules = {}

def load_module(app, commands, prefix, module_name, file_path=None):
    try:
        if file_path is None:
            file_path = f"modules/{module_name}.py"
        
        if module_name in loaded_modules:
            module = importlib.reload(loaded_modules[module_name])
        else:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        
        if hasattr(module, "register"):
            module.register(app, commands, prefix, module_name)
            loaded_modules[module_name] = module
            return True
    except Exception as e:
        print(e)
    return False

def load_modules(app, commands, prefix):
    if not os.path.exists("modules"):
        os.makedirs("modules")
        return {}
    
    for file in os.listdir("modules"):
        if file.endswith(".py"):
            module_name = file[:-3]
            load_module(app, commands, prefix, module_name)
    
    return loaded_modules

def unload_module(module_name):
    if module_name in loaded_modules:
        del loaded_modules[module_name]
    if module_name in sys.modules:
        del sys.modules[module_name]
