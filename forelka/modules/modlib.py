# name: Module Library
# version: 1.0.0
# developer: forelka
# description: Поиск модулей в заданном GitHub-репозитории и выдача ссылок/команд для установки через .dlm.

import asyncio
import difflib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
from pyrogram.enums import ParseMode


# --- Настройки каталога модулей ---
# Укажи здесь репозиторий с .py модулями, которые можно ставить через .dlm
MODULES_OWNER = "kirillusha"
MODULES_REPO = "forelka-userbot-modules"
MODULES_BRANCH = "main"
# Папка внутри репо, где лежат .py модули (можно оставить пустой строкой)
MODULES_PATH = "modules"

# Сколько результатов показывать
MAX_RESULTS = 10


@dataclass
class RepoFile:
    name: str
    path: str
    html_url: str
    download_url: str


def _api_url_for_dir(path: str) -> str:
    base = f"https://api.github.com/repos/{MODULES_OWNER}/{MODULES_REPO}/contents"
    if path:
        return f"{base}/{path}?ref={MODULES_BRANCH}"
    return f"{base}?ref={MODULES_BRANCH}"


def _raw_url_for_path(path: str) -> str:
    # Прямая ссылка на raw (на случай, если download_url отсутствует)
    return f"https://raw.githubusercontent.com/{MODULES_OWNER}/{MODULES_REPO}/{MODULES_BRANCH}/{path}"


def _is_module_filename(filename: str) -> bool:
    if not filename.endswith(".py"):
        return False
    if filename.startswith("_"):
        return False
    if filename == "__init__.py":
        return False
    return True


def _request_json(url: str) -> Any:
    r = requests.get(
        url,
        timeout=12,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "forelka-modlib",
        },
    )
    r.raise_for_status()
    return r.json()


async def _request_json_async(url: str) -> Any:
    return await asyncio.to_thread(_request_json, url)


async def _list_py_files_recursive(path: str, depth: int = 3) -> List[RepoFile]:
    """
    Рекурсивно обходит папку в GitHub репо и собирает .py файлы.
    depth ограничивает вложенность.
    """
    if depth <= 0:
        return []

    data = await _request_json_async(_api_url_for_dir(path))
    if not isinstance(data, list):
        return []

    out: List[RepoFile] = []
    for item in data:
        try:
            t = item.get("type")
            item_path = item.get("path", "")
            name = item.get("name", "")
            if t == "dir":
                out.extend(await _list_py_files_recursive(item_path, depth=depth - 1))
                continue
            if t != "file":
                continue
            if not _is_module_filename(name):
                continue
            out.append(
                RepoFile(
                    name=name[:-3].lower(),
                    path=item_path,
                    html_url=item.get("html_url") or "",
                    download_url=item.get("download_url") or _raw_url_for_path(item_path),
                )
            )
        except Exception:
            continue
    return out


def _score(query: str, mod_name: str) -> float:
    q = query.lower().strip()
    n = mod_name.lower().strip()
    if not q or not n:
        return 0.0
    if q == n:
        return 2.0
    if q in n:
        return 1.5 + (len(q) / max(len(n), 1)) * 0.3
    return difflib.SequenceMatcher(a=q, b=n).ratio()


def _format_results(query: str, results: List[Tuple[float, RepoFile]]) -> str:
    header = (
        f"<emoji id=5897962422169243693>👻</emoji> <b>Module library</b>\n"
        f"<blockquote><b>Query:</b> <code>{query}</code>\n"
        f"<b>Repo:</b> <code>{MODULES_OWNER}/{MODULES_REPO}@{MODULES_BRANCH}</code></blockquote>\n\n"
    )
    if not results:
        return header + "<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Ничего не найдено</b></blockquote>"

    lines = []
    for i, (sc, f) in enumerate(results[:MAX_RESULTS], start=1):
        # Команда для установки через встроенный .dlm
        dlm = f".dlm {f.download_url} {f.name}"
        lines.append(
            "<blockquote>"
            f"<b>{i}.</b> <code>{f.name}</code> "
            f"(score: <code>{sc:.2f}</code>)\n"
            f"<b>Install:</b> <code>{dlm}</code>\n"
            f"<b>Link:</b> <a href=\"{f.html_url}\">repo file</a>"
            "</blockquote>"
        )

    footer = (
        "\n<blockquote>"
        "<b>Подсказка:</b> чтобы поставить модуль — скопируй строку <code>.dlm ...</code> и отправь её себе.\n"
        "Показать установленные: <code>.lm</code>"
        "</blockquote>"
    )
    return header + "\n".join(lines) + footer


async def modsearch_cmd(client, message, args):
    if not args:
        return await message.edit(
            "<blockquote><emoji id=5775887550262546277>❗️</emoji> <b>Usage:</b> <code>.modsearch &lt;query&gt;</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    query = " ".join(args).strip()
    await message.edit(
        "<blockquote><emoji id=5891211339170326418>⌛️</emoji> <b>Searching modules...</b></blockquote>",
        parse_mode=ParseMode.HTML,
    )

    try:
        files = await _list_py_files_recursive(MODULES_PATH, depth=4)
        scored: List[Tuple[float, RepoFile]] = [( _score(query, f.name), f) for f in files]
        scored = [x for x in scored if x[0] >= 0.35]
        scored.sort(key=lambda x: x[0], reverse=True)
        text = _format_results(query, scored)
        await message.edit(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        await message.edit(
            f"<blockquote><emoji id=5778527486270770928>❌</emoji> <b>Error:</b> <code>{e}</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )


def register(app, commands, module_name):
    commands["modsearch"] = {"func": modsearch_cmd, "module": module_name, "description": "Поиск модулей в репозитории модулей."}

