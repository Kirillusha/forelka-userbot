from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ModuleMeta:
    lib: str
    developer: str
    description: str


def normalize_module_meta(
    module_name: str,
    raw: Optional[Dict[str, Any]],
    *,
    default_lib: str,
) -> ModuleMeta:
    raw = raw or {}
    lib = str(raw.get("lib") or default_lib).strip() or default_lib
    developer = str(raw.get("developer") or "unknown").strip() or "unknown"
    description = str(raw.get("description") or "").strip()
    # На всякий случай делаем коротко, чтобы вывод не ломал сообщение
    if len(description) > 600:
        description = description[:597] + "..."
    return ModuleMeta(lib=lib, developer=developer, description=description)

