from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class ModuleMeta:
    # Источник модуля: system/external/legacy (встроенный / загруженный / старый формат).
    lib: str
    # Отображаемое имя модуля (например "TicTacToe")
    name: str
    # Версия (например "2.0.0")
    version: str
    # Разработчик (например "@hikarimods")
    developer: str
    description: str
    pip: Tuple[str, ...]  # pip-пакеты, которые нужно установить для модуля


def normalize_module_meta(
    module_name: str,
    raw: Optional[Dict[str, Any]],
    *,
    default_lib: str,
) -> ModuleMeta:
    raw = raw or {}
    lib = str(raw.get("lib") or default_lib).strip() or default_lib
    name = str(raw.get("name") or raw.get("title") or module_name).strip() or module_name
    version = str(raw.get("version") or raw.get("ver") or "0.0.0").strip() or "0.0.0"
    developer = str(raw.get("developer") or "unknown").strip() or "unknown"
    description = str(raw.get("description") or "").strip()
    pip_raw = raw.get("pip") or raw.get("libs") or raw.get("requirements") or ()
    pip_list = []
    if isinstance(pip_raw, (list, tuple, set)):
        for x in pip_raw:
            try:
                s = str(x).strip()
            except Exception:
                continue
            if not s:
                continue
            pip_list.append(s)
    elif isinstance(pip_raw, str):
        for part in pip_raw.replace(",", " ").split():
            part = part.strip()
            if part:
                pip_list.append(part)

    # На всякий случай делаем коротко, чтобы вывод не ломал сообщение
    if len(description) > 600:
        description = description[:597] + "..."
    # Нормализуем/дедуп по порядку
    seen = set()
    pip_norm = []
    for p in pip_list:
        if p in seen:
            continue
        seen.add(p)
        pip_norm.append(p)
    return ModuleMeta(
        lib=lib,
        name=name,
        version=version,
        developer=developer,
        description=description,
        pip=tuple(pip_norm),
    )

