import json
import os

CONFIG_SECTION = "modules_config"


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
    def __init__(self, client, module_name, defaults=None):
        self.client = client
        self.module_name = module_name
        self.defaults = defaults or {}
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
        module_cfg[key] = value
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
