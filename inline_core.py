import ast
import glob
import json
import os
import random
import re
import time
from typing import Iterable, List, Optional, Set, Tuple


LOG_FILE = os.environ.get("FORELKA_LOG_FILE", "forelka.log")


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _format_uptime(seconds: float) -> str:
    s = int(max(0, seconds))
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    out = []
    if d:
        out.append(f"{d}д")
    if h:
        out.append(f"{h}ч")
    if m:
        out.append(f"{m}м")
    out.append(f"{s}с")
    return " ".join(out)


def get_api_credentials() -> Tuple[int, str]:
    api_id_env = (os.environ.get("FORELKA_API_ID") or "").strip()
    api_hash_env = (os.environ.get("FORELKA_API_HASH") or "").strip()
    if api_id_env and api_hash_env:
        return int(api_id_env), api_hash_env

    candidates = sorted(glob.glob("telegram_api-*.json"), key=lambda p: os.path.getmtime(p))
    for p in reversed(candidates):
        data = _read_json(p) or {}
        try:
            api_id = int(data.get("api_id"))
            api_hash = str(data.get("api_hash") or "").strip()
            if api_id and api_hash:
                return api_id, api_hash
        except Exception:
            continue
    raise RuntimeError("API creds not found (set FORELKA_API_ID/FORELKA_API_HASH or create telegram_api-*.json)")


def get_inline_owners() -> Set[int]:
    owners: Set[int] = set()
    raw = (os.environ.get("FORELKA_INLINE_OWNERS") or "").strip()
    if raw:
        for x in raw.split(","):
            x = x.strip()
            if not x:
                continue
            try:
                owners.add(int(x))
            except Exception:
                pass

    for p in glob.glob("config-*.json"):
        data = _read_json(p) or {}
        for x in (data.get("owners") or []):
            try:
                owners.add(int(x))
            except Exception:
                pass
    return owners


def _tail_lines(path: str, n: int) -> List[str]:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 4096
            buf = b""
            pos = size
            while pos > 0 and buf.count(b"\n") <= n + 2:
                step = block if pos >= block else pos
                pos -= step
                f.seek(pos)
                buf = f.read(step) + buf
            lines = buf.splitlines()[-n:]
            return [x.decode("utf-8", errors="ignore") for x in lines]
    except Exception:
        return []


def tail_log_text(n: int = 40, limit: int = 3500) -> str:
    n = max(1, min(800, int(n)))
    if not os.path.exists(LOG_FILE):
        return "<b>Лог не найден</b>"
    lines = _tail_lines(LOG_FILE, n)
    if not lines:
        return "<b>Лог пуст</b>"
    text = "\n".join(lines).strip()
    if len(text) > limit:
        text = text[-limit:]
    return "<b>forelka.log</b>\n<blockquote expandable><code>" + _escape(text) + "</code></blockquote>"


def search_log_text(needle: str, max_results: int = 25, limit: int = 3500) -> str:
    needle = (needle or "").strip()
    if not needle:
        return "<b>Пустой запрос</b>"
    if not os.path.exists(LOG_FILE):
        return "<b>Лог не найден</b>"

    out = []
    low = needle.lower()
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if low in line.lower():
                    out.append(line.rstrip("\n"))
                    if len(out) >= max_results:
                        break
    except Exception:
        return "<b>Ошибка чтения лога</b>"

    if not out:
        return "<b>Ничего не найдено</b>"
    text = "\n".join(out).strip()
    if len(text) > limit:
        text = text[:limit]
    return "<b>Поиск:</b> <code>" + _escape(needle) + "</code>\n<blockquote expandable><code>" + _escape(text) + "</code></blockquote>"


def build_status_text(start_time: float) -> str:
    up = _format_uptime(time.time() - start_time)
    log_state = "есть" if os.path.exists(LOG_FILE) else "нет"
    return "<b>Forelka</b>\n<blockquote>Аптайм: <code>" + up + "</code>\nЛог: <code>" + log_state + "</code></blockquote>"


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _py_files() -> Iterable[str]:
    for p in ["main.py", "loader.py", "modules", "loaded_modules"]:
        if os.path.isdir(p):
            for f in glob.glob(os.path.join(p, "*.py")):
                yield f
        elif os.path.isfile(p):
            yield p


def list_userbot_commands() -> List[str]:
    cmds: Set[str] = set()
    for path in _py_files():
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                src = f.read()
            tree = ast.parse(src)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    k = _extract_commands_key(t)
                    if k:
                        cmds.add(k)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "update":
                    if node.args:
                        d = _extract_dict_keys(node.args[0])
                        for k in d:
                            cmds.add(k)

    res = sorted(cmds)
    if not res:
        return ["(нет)"]
    return [f"<code>{_escape(x)}</code>" for x in res]


def _extract_commands_key(target: ast.AST) -> Optional[str]:
    if not isinstance(target, ast.Subscript):
        return None
    v = target.value
    if not isinstance(v, ast.Name) or v.id != "commands":
        return None
    sl = target.slice
    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
        return sl.value
    if isinstance(sl, ast.Index) and isinstance(sl.value, ast.Constant) and isinstance(sl.value.value, str):
        return sl.value.value
    return None


def _extract_dict_keys(node: ast.AST) -> List[str]:
    if not isinstance(node, ast.Dict):
        return []
    out = []
    for k in node.keys:
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            out.append(k.value)
    return out


def gen_bot_username(prefix: str = "forelka_", n: int = 5, suffix: str = "_bot") -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    mid = "".join(random.choice(alphabet) for _ in range(max(1, int(n))))
    return f"{prefix}{mid}{suffix}"

