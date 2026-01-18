import asyncio
import json
import os
import re
from typing import Any, Dict, Optional

import requests

INLINE_CONFIG_PATH = os.environ.get("FORELKA_INLINE_CONFIG", "inline_bot.json")
_EMOJI_TAG_RE = re.compile(r"</?emoji[^>]*>")


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data is not None else default
    except Exception:
        return default


def _save_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=True)


def load_inline_config(path: str = INLINE_CONFIG_PATH) -> Dict[str, Any]:
    return _load_json(path, {})


def save_inline_config(path: str, config: Dict[str, Any]) -> None:
    _save_json(path, config)


def _bot_api_request(token: str, method: str, payload: Dict[str, Any], files=None) -> Dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    if files:
        resp = requests.post(url, data=payload, files=files, timeout=20)
    else:
        resp = requests.post(url, json=payload, timeout=15)
    try:
        return resp.json()
    except Exception:
        return {"ok": False, "error_code": resp.status_code, "description": "Invalid JSON"}


def sanitize_html(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    clean = _EMOJI_TAG_RE.sub("", text)
    clean = clean.replace("<blockquote expandable>", "<blockquote>")
    return clean


def ensure_inline_identity() -> Optional[Dict[str, Any]]:
    cfg = load_inline_config()
    token = cfg.get("token")
    if not token:
        return None
    if cfg.get("username") and cfg.get("id"):
        return cfg
    resp = _bot_api_request(token, "getMe", {})
    if resp.get("ok"):
        result = resp.get("result", {})
        cfg["id"] = result.get("id")
        cfg["username"] = result.get("username")
        save_inline_config(INLINE_CONFIG_PATH, cfg)
        return cfg
    return cfg


async def send_bot_message(
    token: str,
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    thread_id: Optional[int] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {"chat_id": chat_id, "text": sanitize_html(text), "parse_mode": parse_mode}
    if thread_id:
        payload["message_thread_id"] = thread_id
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await asyncio.to_thread(_bot_api_request, token, "sendMessage", payload)


def _send_document_sync(
    token: str,
    chat_id: int,
    file_path: str,
    caption: Optional[str],
    parse_mode: str,
    thread_id: Optional[int],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"chat_id": chat_id}
    if caption:
        payload["caption"] = sanitize_html(caption)
        payload["parse_mode"] = parse_mode
    if thread_id:
        payload["message_thread_id"] = thread_id
    with open(file_path, "rb") as f:
        files = {"document": f}
        return _bot_api_request(token, "sendDocument", payload, files=files)


async def send_bot_document(
    token: str,
    chat_id: int,
    file_path: str,
    caption: Optional[str] = None,
    parse_mode: str = "HTML",
    thread_id: Optional[int] = None,
) -> Dict[str, Any]:
    return await asyncio.to_thread(
        _send_document_sync, token, chat_id, file_path, caption, parse_mode, thread_id
    )
