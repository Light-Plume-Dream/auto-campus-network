import threading
import os
import sys
from io import BytesIO

try:
    from PIL import Image, ImageDraw
    import pystray
    from pystray import MenuItem, Menu

    class SystemTray:
        def __init__(self, daemon, logger, config_manager, app_root=None):
            self.daemon = daemon
            self.logger = logger
            self.config_manager = config_manager
            self.app_root = app_root
            self._icon = None
            self._thread = None

        def _create_icon_image(self):
            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            r = int(size * 0.2)
            draw.rounded_rectangle(
                [(0, 0), (size - 1, size - 1)],
                radius=r,
                fill=(42, 157, 255, 255),
            )
            cx, cy = size // 2, size // 2
            dot_radius = int(size * 0.08)
            left_x = int(size * 0.2)
            right_x = int(size * 0.8)
            draw.ellipse(
                [(left_x - dot_radius, cy - dot_radius), (left_x + dot_radius, cy + dot_radius)],
                fill=(255, 255, 255, 255),
            )
            draw.ellipse(
                [(right_x - dot_radius, cy - dot_radius), (right_x + dot_radius, cy + dot_radius)],
                fill=(255, 255, 255, 255),
            )
            line_width = int(size * 0.05)
            top_y = int(size * 0.32)
            draw.line([(left_x, cy), (cx, top_y)], fill=(255, 255, 255, 255), width=line_width)
            draw.line([(right_x, cy), (cx, top_y)], fill=(255, 255, 255, 255), width=line_width)
            draw.line([(cx, top_y), (cx, int(size * 0.68))], fill=(255, 255, 255, 255), width=line_width)
            return img

        def _show_logs(self):
            if self.app_root:
                self.app_root.after(0, self.app_root._show_logs)
            else:
                logs = self.logger.get_recent_logs(100)
                for line in logs:
                    print(line)

        def _toggle_connection(self):
            if self.daemon.is_running():
                if self.daemon.is_paused():
                    self.daemon.resume()
                else:
                    self.daemon.pause()
            else:
                cfg = self.config_manager.get_config()
                self.daemon = type(self.daemon)(cfg, self.logger)
                self.daemon.start()

        def _quit(self):
            if self.daemon:
                self.daemon.stop()
            if self._icon:
                self._icon.stop()
            if self.app_root:
                self.app_root.after(0, self.app_root.quit)

        def _build_menu(self):
            return Menu(
                MenuItem("显示窗口", self._show_window, default=True),
                MenuItem("暂停/恢复", self._toggle_connection),
                MenuItem("查看日志", self._show_logs),
                Menu.SEPARATOR,
                MenuItem("退出", self._quit),
            )

        def _show_window(self):
            if self.app_root:
                self.app_root.after(0, self.app_root.root.deiconify)

        def start(self):
            self._thread = threading.Thread(target=self._run_tray, daemon=True)
            self._thread.start()

        def _run_tray(self):
            icon = pystray.Icon("campus_network")
            icon.title = "自动校园网连接"
            icon.icon = self._create_icon_image()
            icon.menu = self._build_menu()
            self._icon = icon
            icon.run()

        def stop(self):
            if self._icon:
                self._icon.stop()

except ImportError:
    class SystemTray:
        def __init__(self, daemon, logger, config_manager, app_root=None):
            self.daemon = daemon
            self.logger = logger
            self.config_manager = config_manager
            self.app_root = app_root

        def start(self):
            pass

        def stop(self):
            pass
