import json
import os
import threading
from pathlib import Path
from datetime import datetime


class Logger:
    def __init__(self, log_dir=None, max_lines=5000):
        if log_dir is None:
            log_dir = Path(__file__).parent / "logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self.log_dir / f"connection_{datetime.now().strftime('%Y%m')}.log"
        self._lock = threading.Lock()
        self.max_lines = max_lines  # 日志文件最大行数，超过则自动清理旧日志

    def _get_log_file(self):
        new_file = self.log_dir / f"connection_{datetime.now().strftime('%Y%m')}.log"
        if new_file != self._log_file:
            self._log_file = new_file
        return self._log_file

    def _cleanup_old_logs(self):
        """清理旧日志，只保留最新的 max_lines 行"""
        try:
            log_file = self._get_log_file()
            if not log_file.exists():
                return
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > self.max_lines:
                with open(log_file, "w", encoding="utf-8") as f:
                    f.writelines(lines[-self.max_lines:])
        except Exception:
            pass

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        with self._lock:
            with open(self._get_log_file(), "a", encoding="utf-8") as f:
                f.write(log_entry)
            # 定期清理旧日志（每写 100 条检查一次）
            if os.path.getsize(self._get_log_file()) > 1024 * 1024:  # 超过 1MB
                self._cleanup_old_logs()

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
