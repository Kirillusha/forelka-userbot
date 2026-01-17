import json
import os
import sys

CONFIG_SECTION = "modules_config"
CONFIG_REGISTRY = {}


def _infer_type(value):
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "list"
    return "str"


def normalize_schema(schema):
    if not isinstance(schema, dict):
        return {}

    normalized = {}
    for key, spec in schema.items():
        if isinstance(spec, dict):
            default = spec.get("default")
            type_id = spec.get("type") or _infer_type(default)
            doc = spec.get("doc") or spec.get("description") or ""
            choices = spec.get("choices") or []
            hidden = bool(spec.get("hidden", False))
        else:
            default = spec
            type_id = _infer_type(default)
            doc = ""
            choices = []
            hidden = False

        normalized[str(key)] = {
            "default": default,
            "type": str(type_id),
            "doc": str(doc),
            "choices": list(choices) if isinstance(choices, (list, tuple, set)) else [],
            "hidden": hidden,
        }
    return normalized


def register_config(module_name, schema):
    if not module_name:
        return
    CONFIG_REGISTRY[str(module_name)] = normalize_schema(schema)


def get_config_schema(module_name):
    if not module_name:
        return {}
    name = str(module_name)
    schema = CONFIG_REGISTRY.get(name)
    if schema:
        return schema

    mod = sys.modules.get(name)
    raw = getattr(mod, "CONFIG_SCHEMA", None) if mod else None
    if raw is None and mod is not None:
        raw = getattr(mod, "CONFIG", None)
    if raw:
        schema = normalize_schema(raw)
        CONFIG_REGISTRY[name] = schema
        return schema

    return {}


def validate_value(value, schema_item):
    if not schema_item:
        return value

    type_id = schema_item.get("type")
    choices = schema_item.get("choices") or []

    if type_id == "bool":
        if isinstance(value, bool):
            return value
        raise ValueError("Expected boolean")

    if type_id == "int":
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        raise ValueError("Expected integer")

    if type_id == "float":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        raise ValueError("Expected float")

    if type_id == "list":
        if isinstance(value, list):
            return value
        raise ValueError("Expected list")

    if type_id == "choice":
        if value in choices:
            return value
        raise ValueError("Value not in choices")

    if type_id == "multi_choice":
        if isinstance(value, list):
            invalid = [v for v in value if v not in choices]
            if invalid:
                raise ValueError("Value not in choices")
            return value
        raise ValueError("Expected list")

    return value


def _load_config(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_config(path, cfg):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


class ModuleConfig:
    def __init__(self, client, module_name, defaults=None, schema=None):
        self.client = client
        self.module_name = module_name
        if schema:
            self.schema = normalize_schema(schema)
            register_config(module_name, self.schema)
        else:
            self.schema = get_config_schema(module_name)
        self.defaults = defaults or {
            key: item.get("default")
            for key, item in self.schema.items()
            if isinstance(item, dict) and "default" in item
        }
        self.config_path = f"config-{client.me.id}.json"

    def _section(self, cfg, create=False):
        section = cfg.get(CONFIG_SECTION)
        if not isinstance(section, dict):
            section = {}
            if create:
                cfg[CONFIG_SECTION] = section
        return section

    def _module_cfg(self, cfg, create=False):
        section = self._section(cfg, create=create)
        module_cfg = section.get(self.module_name)
        if not isinstance(module_cfg, dict):
            module_cfg = {}
            if create:
                section[self.module_name] = module_cfg
        return module_cfg

    def get(self, key, default=None):
        cfg = _load_config(self.config_path)
        module_cfg = self._module_cfg(cfg, create=False)
        if key in module_cfg:
            return module_cfg.get(key)
        if key in self.defaults:
            return self.defaults.get(key)
        return default

    def set(self, key, value):
        cfg = _load_config(self.config_path)
        module_cfg = self._module_cfg(cfg, create=True)
        schema_item = self.schema.get(key) if isinstance(self.schema, dict) else None
        module_cfg[key] = validate_value(value, schema_item)
        _save_config(self.config_path, cfg)

    def delete(self, key):
        cfg = _load_config(self.config_path)
        section = self._section(cfg, create=False)
        module_cfg = self._module_cfg(cfg, create=False)
        if key in module_cfg:
            module_cfg.pop(key, None)
            if not module_cfg and self.module_name in section:
                section.pop(self.module_name, None)
            _save_config(self.config_path, cfg)

    def all(self):
        cfg = _load_config(self.config_path)
        module_cfg = self._module_cfg(cfg, create=False)
        merged = dict(self.defaults)
        merged.update(module_cfg)
        return merged
