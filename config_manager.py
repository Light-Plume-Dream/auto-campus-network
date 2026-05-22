import json
import os
import sys
from pathlib import Path
import threading


DEFAULT_CONFIG = {
    "connection_name": "",
    "username": "",
    "password": "",
    "work_time_start": "06:00",
    "work_time_end": "22:30",
    "retry_limit": 30,
    "retry_interval": 10,
    "check_interval": 30,
    "sleep_interval": 600,
    "wol_mac": "",
    "wol_port": 55555,
}


class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is None:
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = Path(base_dir) / "config.json"
        self.config_path = Path(config_path)
        self._lock = threading.Lock()

    def get_config(self) -> dict:
        with self._lock:
            if not self.config_path.exists():
                return DEFAULT_CONFIG.copy()
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                    cfg = DEFAULT_CONFIG.copy()
                    cfg.update(stored)
                    return cfg
            except Exception:
                return DEFAULT_CONFIG.copy()

    def save_config(self, config: dict) -> bool:
        with self._lock:
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                return True
            except Exception:
                return False

    def get(self, key: str, default=None):
        cfg = self.get_config()
        return cfg.get(key, default)
