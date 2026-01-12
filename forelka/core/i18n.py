import os
from typing import Any, Dict, Optional

import yaml


def _deep_get(d: Dict[str, Any], key: str) -> Any:
    cur: Any = d
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _safe_format(value: str, **kwargs) -> str:
    # Не падаем, если не хватает плейсхолдеров.
    class _SafeDict(dict):
        def __missing__(self, k):
            return "{" + k + "}"

    try:
        return value.format_map(_SafeDict(**kwargs))
    except Exception:
        return value


class Translator:
    """
    Простая i18n:
    - base (например ru) содержит полный набор строк
    - lang может переопределять часть строк
    - если ключ отсутствует, вернём base -> default -> key
    """

    def __init__(self, base: Dict[str, Any], lang: Dict[str, Any]):
        self.base = base or {}
        self.lang = lang or {}

    def t(self, key: str, default: Optional[str] = None, **fmt) -> str:
        val = _deep_get(self.lang, key)
        if val is None:
            val = _deep_get(self.base, key)
        if val is None:
            val = default if default is not None else key
        if not isinstance(val, str):
            val = str(val)
        return _safe_format(val, **fmt)


def languages_dir() -> str:
    # /workspace/languages (папка рядом с пакетом forelka/)
    here = os.path.abspath(os.path.dirname(__file__))          # forelka/core
    pkg = os.path.abspath(os.path.join(here, os.pardir))       # forelka
    root = os.path.abspath(os.path.join(pkg, os.pardir))       # workspace root
    return os.path.join(root, "languages")


def list_languages() -> Dict[str, str]:
    """
    Возвращает {code: filename}.
    Поддерживаем *.yml и *.yaml
    """
    d = languages_dir()
    out: Dict[str, str] = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not (fn.endswith(".yml") or fn.endswith(".yaml")):
            continue
        code = fn.rsplit(".", 1)[0].lower()
        out[code] = os.path.join(d, fn)
    return out


def load_pack(code: str) -> Dict[str, Any]:
    paths = list_languages()
    path = paths.get(code.lower())
    if not path:
        raise FileNotFoundError(f"Language pack not found: {code}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid language pack format: {code}")
    return data


def build_translator(lang_code: str, base_code: str = "ru") -> Translator:
    base = load_pack(base_code)
    lang = base if lang_code.lower() == base_code.lower() else load_pack(lang_code)
    return Translator(base=base, lang=lang)

