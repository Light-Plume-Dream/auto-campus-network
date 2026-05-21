import json
import os
import threading
from pathlib import Path
from datetime import datetime


class Logger:
    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = Path(__file__).parent / "logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self.log_dir / f"connection_{datetime.now().strftime('%Y%m')}.log"
        self._lock = threading.Lock()

    def _get_log_file(self):
        new_file = self.log_dir / f"connection_{datetime.now().strftime('%Y%m')}.log"
        if new_file != self._log_file:
            self._log_file = new_file
        return self._log_file

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        with self._lock:
            with open(self._get_log_file(), "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")

    def info(self, message: str):
        self.log(message, "INFO")

    def warning(self, message: str):
        self.log(message, "WARNING")

    def error(self, message: str):
        self.log(message, "ERROR")

    def success(self, message: str):
        self.log(message, "SUCCESS")

    def get_recent_logs(self, lines: int = 100) -> list:
        try:
            log_file = self._get_log_file()
            if not log_file.exists():
                return []
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                return [line.strip() for line in all_lines[-lines:]]
        except Exception:
            return []

    def clear_logs(self):
        with self._lock:
            for f in self.log_dir.glob("*.log"):
                f.unlink()
