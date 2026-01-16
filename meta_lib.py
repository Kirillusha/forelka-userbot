from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


META_FIELDS = {
    "name",
    "version",
    "author",
    "description",
    "commands",
    "source",
    "repo",
    "docs",
}


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_commands(value: Optional[Iterable[str]]) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        items = [value]
    else:
        items = list(value)
    out: List[str] = []
    seen = set()
    for item in items:
        text = _as_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _merge_commands(base: List[str], extra: Optional[Iterable[str]]) -> List[str]:
    out = list(base or [])
    for item in _normalize_commands(extra):
        if item not in out:
            out.append(item)
    return out


def _coerce_meta(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return dict(raw)
    if hasattr(raw, "to_dict") and callable(raw.to_dict):
        try:
            return dict(raw.to_dict())
        except Exception:
            return None
    if hasattr(raw, "__dict__"):
        try:
            return dict(raw.__dict__)
        except Exception:
            return None
    return None


def build_meta(
    name: str = "",
    version: str = "",
    author: str = "",
    description: str = "",
    commands: Optional[Iterable[str]] = None,
    source: Optional[str] = None,
    repo: Optional[str] = None,
    docs: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "name": _as_text(name),
        "version": _as_text(version),
        "author": _as_text(author),
        "description": _as_text(description),
        "commands": _normalize_commands(commands),
        "source": _as_text(source),
        "repo": _as_text(repo),
        "docs": _as_text(docs),
    }
    if extra:
        meta["extra"] = dict(extra)
    return meta


def normalize_meta(
    raw: Any,
    fallback_name: str,
    commands: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    meta = build_meta(name=fallback_name)
    raw_meta = _coerce_meta(raw)
    extra: Dict[str, Any] = {}
    if raw_meta:
        for key, value in raw_meta.items():
            if key == "commands":
                meta["commands"] = _merge_commands(meta["commands"], value)
                continue
            if key in META_FIELDS:
                text = _as_text(value)
                if text:
                    meta[key] = text
                continue
            extra[key] = value
    if commands:
        meta["commands"] = _merge_commands(meta["commands"], commands)
    if not meta["name"]:
        meta["name"] = _as_text(fallback_name)
    if extra:
        meta["extra"] = extra
    return meta


def read_module_meta(
    module: Any,
    fallback_name: str,
    commands: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    raw = getattr(module, "__meta__", None) if module else None
    meta = normalize_meta(raw, fallback_name=fallback_name, commands=commands)
    if not module:
        return meta

    attr_map = {
        "__author__": "author",
        "__version__": "version",
        "__description__": "description",
        "__repo__": "repo",
        "__docs__": "docs",
        "__source__": "source",
    }
    for attr, key in attr_map.items():
        value = _as_text(getattr(module, attr, ""))
        if value and not meta.get(key):
            meta[key] = value

    if not meta.get("description"):
        doc = _as_text(getattr(module, "__doc__", ""))
        if doc:
            meta["description"] = doc.splitlines()[0].strip()

    return meta
