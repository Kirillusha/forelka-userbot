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



COMMAND_INFO_KEYS = (

    "commands_info",

    "command_descriptions",

    "commands_desc",

    "commands_help",

    "cmds_info",

)





def _as_text(value: Any) -> str:

    if value is None:

        return ""

    return str(value).strip()





def _normalize_command_name(value: Any) -> str:

    text = _as_text(value)

    if not text:

        return ""

    text = text.strip()

    if text and text[0] in (".", "/", "!", "?"):

        text = text[1:]

    return text.strip().lower()





def _parse_commands_value(value: Any) -> Dict[str, str]:

    result: Dict[str, str] = {}

    if value is None:

        return result

    if isinstance(value, dict):

        for key, val in value.items():

            name = _normalize_command_name(key)

            if not name:

                continue

            if isinstance(val, dict):

                desc = val.get("description") or val.get("desc") or val.get("about") or ""

            else:

                desc = val

            result[name] = _as_text(desc)

        return result

    if isinstance(value, (list, tuple, set)):

        for item in value:

            if isinstance(item, dict):

                name = item.get("name") or item.get("command") or item.get("cmd")

                desc = item.get("description") or item.get("desc") or item.get("about")

                if not name and len(item) == 1:

                    key, val = next(iter(item.items()))

                    name = key

                    desc = val

                name = _normalize_command_name(name)

                if name:

                    result[name] = _as_text(desc)

                continue

            text = _as_text(item)

            if not text:

                continue

            name = text

            desc = ""

            for sep in (" — ", " - ", ": "):

                if sep in text:

                    name, desc = text.split(sep, 1)

                    break

            name = _normalize_command_name(name)

            if name:

                result[name] = _as_text(desc)

        return result

    text = _as_text(value)

    if text:

        name = text

        desc = ""

        for sep in (" — ", " - ", ": "):

            if sep in text:

                name, desc = text.split(sep, 1)

                break

        name = _normalize_command_name(name)

        if name:

            result[name] = _as_text(desc)

    return result





def extract_command_descriptions(raw: Any) -> Dict[str, str]:

    meta = _coerce_meta(raw) or {}

    result: Dict[str, str] = {}

    candidates = []

    if "commands" in meta:

        candidates.append(meta.get("commands"))

    for key in COMMAND_INFO_KEYS:

        if key in meta:

            candidates.append(meta.get(key))

    extra = meta.get("extra")

    if isinstance(extra, dict):

        if "commands" in extra:

            candidates.append(extra.get("commands"))

        for key in COMMAND_INFO_KEYS:

            if key in extra:

                candidates.append(extra.get(key))

    for candidate in candidates:

        parsed = _parse_commands_value(candidate)

        if parsed:

            result.update(parsed)

    return result





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
