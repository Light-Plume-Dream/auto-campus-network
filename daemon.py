import subprocess
import time
import threading
import os
from logger import Logger

# 隐藏 Windows 控制台窗口
SW_HIDE = 0
startupinfo = None
if os.name == 'nt':
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = SW_HIDE


class ConnectionDaemon:
    def __init__(self, config, logger=None, status_callback=None):
        self.config = config
        self.logger = logger or Logger()
        self.status_callback = status_callback
        self._running = False
        self._paused = False
        self._thread = None

    def _notify_status(self, status: str, message: str = ""):
        if self.status_callback:
            self.status_callback(status, message)

    def _is_within_work_time(self) -> bool:
        start = self.config.get("work_time_start", "06:00")
        end = self.config.get("work_time_end", "22:30")
        now = time.strftime("%H:%M")
        return start <= now <= end

    def _run_cmd(self, args, timeout=30):
        """执行命令并隐藏控制台窗口"""
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            self.logger.error(f"执行命令失败: {e}")
            return -1, "", str(e)

    def _is_connected(self) -> bool:
        conn_name = self.config.get("connection_name", "")
        retcode, stdout, stderr = self._run_cmd(["rasdial"], timeout=10)
        return conn_name in stdout

    def _dial(self) -> bool:
        conn_name = self.config.get("connection_name", "")
        user = self.config.get("username", "")
        password = self.config.get("password", "")
        retcode, stdout, stderr = self._run_cmd(
            ["rasdial", conn_name, user, password], timeout=30
        )
        if retcode != 0:
            self.logger.error(f"拨号失败: {stderr}")
        return retcode == 0

    def _run_loop(self):
        self._notify_status("started", "自动连接守护进程已启动")
        retry_limit = self.config.get("retry_limit", 30)
        retry_interval = self.config.get("retry_interval", 10)
        check_interval = self.config.get("check_interval", 30)

        while self._running:
            if self._paused:
                time.sleep(1)
                continue

            if not self._is_within_work_time():
                time.sleep(10)
                continue

            if self._is_connected():
                time.sleep(check_interval)
                continue

            self.logger.warning("检测到断开，开始拨号...")
            self._notify_status("connecting", "检测到断开，正在拨号...")

            retry = 0
            while self._running and not self._paused:
                if self._dial():
                    self.logger.success("拨号成功")
                    self._notify_status("connected", "拨号成功")
                    time.sleep(check_interval)
                    break

                retry += 1
                self.logger.warning(f"拨号失败，第 {retry} 次重试...")
                self._notify_status("retry", f"拨号失败，第 {retry} 次重试...")

                if retry >= retry_limit:
                    self.logger.error(f"拨号失败已达 {retry_limit} 次，等待 5 分钟后重试...")
                    self._notify_status("failed", f"拨号失败 {retry_limit} 次，5 分钟后重试")
                    time.sleep(300)
                    break

                time.sleep(retry_interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._notify_status("stopped", "自动连接守护进程已停止")

    def pause(self):
        self._paused = True
        self._notify_status("paused", "自动连接已暂停")

    def resume(self):
        self._paused = False
        self._notify_status("resumed", "自动连接已恢复")

    def is_running(self) -> bool:
        return self._running

    def is_paused(self) -> bool:
        return self._paused
