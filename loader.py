import importlib.util
import os
import sys
import inspect
import requests
import shutil
from git import Repo, GitCommandError

from pyrogram.enums import ParseMode

def is_protected(name):
    return os.path.exists(f"modules/{name}.py") or name in ["loader", "main"]

async def dlm_cmd(client, message, args):
    if len(args) < 2: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .dlm [url] [name]</b></blockquote>", parse_mode=ParseMode.HTML)
    
    url, name = args[0], args[1].lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    path = f"loaded_modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Downloading {name}...</b></blockquote>", parse_mode=ParseMode.HTML)
    
    try:
        r = requests.get(url, timeout=10)
        with open(path, "wb") as f: 
            f.write(r.content)
            
        if load_module(client, name, "loaded_modules"):
            await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} installed</b></blockquote>", parse_mode=ParseMode.HTML)
        else: 
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: 
        await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>", parse_mode=ParseMode.HTML)

async def lm_cmd(client, message, args):
    if not message.reply_to_message or not message.reply_to_message.document:
        out = "<blockquote><b>Modules:</b>\n" + "\n".join([f" • <code>{m}</code>" for m in sorted(client.loaded_modules)]) + "</blockquote>"
        return await message.edit(out, parse_mode=ParseMode.HTML)
    
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".py"): 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>.py only</b></blockquote>", parse_mode=ParseMode.HTML)
    
    name = (args[0] if args else doc.file_name[:-3]).lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    path = f"loaded_modules/{name}.py"
    await message.edit(f"<blockquote><emoji id=5899757765743615694>⬇️</emoji> <b>Saving {name}...</b></blockquote>", parse_mode=ParseMode.HTML)
    
    try:
        await client.download_media(message.reply_to_message, file_name=path)
        if load_module(client, name, "loaded_modules"): 
            await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} loaded</b></blockquote>", parse_mode=ParseMode.HTML)
        else: 
            await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Load failed</b></blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e: 
        await message.edit(f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>", parse_mode=ParseMode.HTML)

async def ulm_cmd(client, message, args):
    if not args: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ulm [name]</b></blockquote>", parse_mode=ParseMode.HTML)
    
    name = args[0].lower()
    if is_protected(name): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    path = f"loaded_modules/{name}.py"
    if os.path.exists(path):
        unload_module(client, name)
        os.remove(path)
        await message.edit(f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {name} deleted</b></blockquote>", parse_mode=ParseMode.HTML)
    else: 
        await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>", parse_mode=ParseMode.HTML)

async def ml_cmd(client, message, args):
    if not args: 
        return await message.edit("<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .ml [name]</b></blockquote>", parse_mode=ParseMode.HTML)
    
    name = args[0]
    path = f"loaded_modules/{name}.py"
    if not os.path.exists(path): 
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Not found</b></blockquote>", parse_mode=ParseMode.HTML)
    
    await message.delete()
    await client.send_document(
        message.chat.id, 
        path, 
        caption=f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module:</b> <code>{name}</code></blockquote>", 
        parse_mode=ParseMode.HTML
    )

async def dlmr_cmd(client, message, args):
    """Download module from repository: .dlmr <repo_url> [module_name]"""
    if len(args) < 1:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .dlmr [repo_url] [module_name]</b>\n\n"
            "<b>Examples:</b>\n"
            "<code>.dlmr https://github.com/user/repo module_name</code>\n"
            "<code>.dlmr https://github.com/user/repo</code> (loads all modules)</blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    repo_url = args[0]
    module_name = args[1].lower() if len(args) > 1 else None
    
    if module_name and is_protected(module_name):
        return await message.edit("<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Access Denied</b></blockquote>", parse_mode=ParseMode.HTML)
    
    await message.edit(
        f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Cloning repository...</b></blockquote>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        repos_dir = "repositories"
        repo_path = os.path.join(repos_dir, repo_name)
        
        # Create repositories directory if not exists
        if not os.path.exists(repos_dir):
            os.makedirs(repos_dir)
        
        # Clone or pull repository
        if os.path.exists(repo_path):
            await message.edit(
                f"<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Updating repository {repo_name}...</b></blockquote>",
                parse_mode=ParseMode.HTML
            )
            try:
                repo = Repo(repo_path)
                origin = repo.remotes.origin
                origin.pull()
            except:
                shutil.rmtree(repo_path)
                Repo.clone_from(repo_url, repo_path)
        else:
            Repo.clone_from(repo_url, repo_path)
        
        # Find Python modules in repository
        py_files = []
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in root:
                continue
            for file in files:
                if file.endswith('.py') and not file.startswith('_'):
                    py_files.append((os.path.join(root, file), file[:-3]))
        
        if not py_files:
            return await message.edit(
                "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>No Python modules found in repository</b></blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        # If specific module name provided, load only that module
        if module_name:
            target_file = None
            for file_path, name in py_files:
                if name.lower() == module_name:
                    target_file = file_path
                    break
            
            if not target_file:
                return await message.edit(
                    f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Module {module_name} not found in repository</b></blockquote>",
                    parse_mode=ParseMode.HTML
                )
            
            # Copy module to loaded_modules
            dest_path = f"loaded_modules/{module_name}.py"
            shutil.copy2(target_file, dest_path)
            
            if load_module(client, module_name, "loaded_modules"):
                await message.edit(
                    f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Module {module_name} loaded from repository {repo_name}</b></blockquote>",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.edit(
                    "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Failed to load module</b></blockquote>",
                    parse_mode=ParseMode.HTML
                )
        else:
            # Load all modules from repository
            loaded = []
            failed = []
            
            for file_path, name in py_files:
                if is_protected(name):
                    failed.append(f"{name} (protected)")
                    continue
                
                dest_path = f"loaded_modules/{name}.py"
                shutil.copy2(file_path, dest_path)
                
                if load_module(client, name, "loaded_modules"):
                    loaded.append(name)
                else:
                    failed.append(name)
            
            result_text = f"<emoji id=5776375003280838798>✅</emoji> <b>Repository {repo_name} processed</b>\n\n"
            
            if loaded:
                result_text += f"<b>Loaded ({len(loaded)}):</b>\n"
                result_text += "<blockquote>" + "\n".join([f"<emoji id=5877468380125990242>➡️</emoji> <code>{m}</code>" for m in loaded]) + "</blockquote>\n\n"
            
            if failed:
                result_text += f"<b>Failed ({len(failed)}):</b>\n"
                result_text += "<blockquote>" + "\n".join([f"<emoji id=5778527486270770928>❌</emoji> <code>{m}</code>" for m in failed]) + "</blockquote>"
            
            await message.edit(f"<blockquote>{result_text}</blockquote>", parse_mode=ParseMode.HTML)
            
    except GitCommandError as e:
        await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Git Error:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

async def lmr_cmd(client, message, args):
    """List repositories: .lmr"""
    repos_dir = "repositories"
    
    if not os.path.exists(repos_dir):
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>No repositories found</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    repos = [d for d in os.listdir(repos_dir) if os.path.isdir(os.path.join(repos_dir, d)) and not d.startswith('.')]
    
    if not repos:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>No repositories found</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    text = "<emoji id=5897962422169243693>👻</emoji> <b>Downloaded Repositories</b>\n\n"
    
    for repo_name in sorted(repos):
        repo_path = os.path.join(repos_dir, repo_name)
        
        # Count Python modules in repo
        py_count = 0
        for root, dirs, files in os.walk(repo_path):
            if '.git' in root:
                continue
            py_count += len([f for f in files if f.endswith('.py') and not f.startswith('_')])
        
        # Try to get repo URL
        try:
            repo = Repo(repo_path)
            repo_url = list(repo.remotes.origin.urls)[0] if repo.remotes else "unknown"
        except:
            repo_url = "unknown"
        
        text += f"<emoji id=5877468380125990242>➡️</emoji> <b>{repo_name}</b>\n"
        text += f"<blockquote><b>Modules:</b> <code>{py_count}</code>\n"
        text += f"<b>URL:</b> <code>{repo_url}</code></blockquote>\n\n"
    
    await message.edit(text, parse_mode=ParseMode.HTML)

async def rmr_cmd(client, message, args):
    """Remove repository: .rmr <repo_name>"""
    if not args:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage: .rmr [repo_name]</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    repo_name = args[0]
    repo_path = os.path.join("repositories", repo_name)
    
    if not os.path.exists(repo_path):
        return await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Repository {repo_name} not found</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        shutil.rmtree(repo_path)
        await message.edit(
            f"<blockquote><emoji id=5776375003280838798>✅</emoji> <b>Repository {repo_name} removed</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

def load_module(app, name, folder):
    path = os.path.abspath(os.path.join(folder, f"{name}.py"))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        
        reg = getattr(mod, "register", None)
        if reg:
            sig = inspect.signature(reg)
            if len(sig.parameters) == 3:
                reg(app, app.commands, name)
            else:
                reg(app, app.commands)
            app.loaded_modules.add(name)
            return True
    except:
        return False
    return False

def unload_module(app, name):
    to_pop = [k for k, v in list(app.commands.items()) if v.get("module") == name]
    for k in to_pop:
        app.commands.pop(k)
    app.loaded_modules.discard(name)
    if name in sys.modules:
        del sys.modules[name]

def load_all(app):
    app.commands.update({
        "dlm":  {"func": dlm_cmd,  "module": "loader"},
        "lm":   {"func": lm_cmd,   "module": "loader"},
        "ulm":  {"func": ulm_cmd,  "module": "loader"},
        "ml":   {"func": ml_cmd,   "module": "loader"},
        "dlmr": {"func": dlmr_cmd, "module": "loader"},
        "lmr":  {"func": lmr_cmd,  "module": "loader"},
        "rmr":  {"func": rmr_cmd,  "module": "loader"}
    })
    app.loaded_modules.add("loader")
    
    for d in ["modules", "loaded_modules", "repositories"]:
        if not os.path.exists(d):
            os.makedirs(d)
    
    for d in ["modules", "loaded_modules"]:
        for f in sorted(os.listdir(d)):
            if f.endswith(".py") and not f.startswith("_"):
                load_module(app, f[:-3], d)
