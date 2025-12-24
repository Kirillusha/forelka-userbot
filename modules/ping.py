import time

async def ping_cmd(client, message, args):
    start = time.perf_counter()
    await message.edit("Pong")
    end = time.perf_counter()
    ms = (end - start) * 1000
    await message.edit(f"Pong\n{ms:.2f} ms")

def register(app, commands, module_name):
    commands["ping"] = {"func": ping_cmd, "module": module_name}
