import threading
import os
import sys
import ctypes
from pathlib import Path
import win32gui
import win32con
import win32api
from icon_generator import generate_icon


WM_TRAYICON = win32con.WM_USER + 1


class SystemTray:
    def __init__(self, daemon, logger, config_manager, app_root=None):
        self.daemon = daemon
        self.logger = logger
        self.config_manager = config_manager
        self.app_root = app_root
        self.hwnd = None
        self._thread = None
        self._running = False
        self._hicon = None
        self._menu_items = {}

    def _load_icon(self):
        """
        加载托盘图标，优先级：
        1. app_icon.ico（程序目录/打包临时目录）
        2. 从 exe 自身资源提取
        3. 自动生成图标
        4. Windows 默认图标
        """
        # 查找图标文件
        ico_paths = []
        
        # 打包后的临时目录
        if getattr(sys, "frozen", False):
            ico_paths.append(os.path.join(sys._MEIPASS, "app_icon.ico"))
        
        # 当前脚本目录
        ico_paths.append(str(Path(__file__).parent / "app_icon.ico"))

        for ico_path in ico_paths:
            if os.path.exists(ico_path):
                try:
                    return win32gui.LoadImage(
                        0, ico_path,
                        win32con.IMAGE_ICON,
                        0, 0,
                        win32con.LR_LOADFROMFILE
                    )
                except Exception:
                    pass

        # 从 exe 自身资源提取图标（打包后）
        if getattr(sys, "frozen", False):
            try:
                hmod = win32api.GetModuleHandle(None)
                hicon = win32gui.LoadIcon(hmod, 1)
                if hicon:
                    return hicon
            except Exception:
                pass

        # 自动生成
        try:
            generated = generate_icon()
            if generated and os.path.exists(generated):
                return win32gui.LoadImage(
                    0, generated,
                    win32con.IMAGE_ICON,
                    0, 0,
                    win32con.LR_LOADFROMFILE
                )
        except Exception:
            pass

        # Windows 默认图标
        try:
            hmod = win32api.GetModuleHandle(None)
            return win32gui.LoadIcon(hmod, win32con.IDI_APPLICATION)
        except Exception:
            return 0

    def _icon_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            if lparam in (win32con.WM_RBUTTONUP, win32con.WM_CONTEXTMENU):
                self._show_menu()
            elif lparam == win32con.WM_LBUTTONDBLCLK:
                self._show_window()
        elif msg == win32con.WM_COMMAND:
            cmd_id = wparam & 0xFFFF
            if cmd_id in self._menu_items:
                self._menu_items[cmd_id]()
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _show_menu(self):
        menu = win32gui.CreatePopupMenu()
        self._menu_items = {}
        item_id = 1000

        win32gui.AppendMenu(menu, win32con.MF_STRING, item_id, "显示窗口")
        self._menu_items[item_id] = self._show_window
        item_id += 1

        if self.daemon.is_running():
            label = "恢复连接" if self.daemon.is_paused() else "暂停连接"
        else:
            label = "启动连接"
        win32gui.AppendMenu(menu, win32con.MF_STRING, item_id, label)
        self._menu_items[item_id] = self._toggle_connection
        item_id += 1

        win32gui.AppendMenu(menu, win32con.MF_STRING, item_id, "查看日志")
        self._menu_items[item_id] = self._show_logs
        item_id += 1

        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")

        win32gui.AppendMenu(menu, win32con.MF_STRING, item_id, "退出")
        self._menu_items[item_id] = self._quit

        win32gui.SetMenuDefaultItem(menu, 1000, False)

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_RIGHTBUTTON | win32con.TPM_BOTTOMALIGN,
            pos[0], pos[1],
            0, self.hwnd, None
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

    def _show_logs(self):
        if self.app_root:
            self.app_root.after(0, self.app_root._show_logs)

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
        self._running = False
        self._remove_icon()
        if self.hwnd:
            try:
                win32gui.DestroyWindow(self.hwnd)
                self.hwnd = None
            except Exception:
                pass
        if self.app_root:
            self.app_root.after(0, self.app_root.root.quit)

    def _show_window(self):
        if self.app_root:
            def restore():
                root = self.app_root.root
                root.deiconify()
                root.lift()
                root.attributes('-topmost', True)
                root.after(100, lambda: root.attributes('-topmost', False))
                root.focus_force()
            self.app_root.after(0, restore)

    def start(self):
        self._thread = threading.Thread(target=self._run_tray, daemon=True)
        self._thread.start()

    def _run_tray(self):
        self._running = True

        wc = win32gui.WNDCLASS()
        wc.hInstance = win32gui.GetModuleHandle(None)
        wc.lpszClassName = "CampusNetworkTray"
        wc.lpfnWndProc = self._icon_wnd_proc
        class_atom = win32gui.RegisterClass(wc)

        self.hwnd = win32gui.CreateWindow(
            class_atom,
            "TrayIcon",
            win32con.WS_OVERLAPPED | win32con.WS_SYSMENU,
            0, 0,
            win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
            0, 0,
            wc.hInstance, None
        )

        self._hicon = self._load_icon()

        nid = (
            self.hwnd,
            0,
            win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            WM_TRAYICON,
            self._hicon,
            "自动校园网连接"
        )
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        except Exception as e:
            self.logger.error(f"Tray icon error: {e}")

        win32gui.PumpMessages()

    def _remove_icon(self):
        if self.hwnd:
            try:
                nid = (self.hwnd, 0)
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
            except Exception:
                pass

    def stop(self):
        self._running = False
        self._remove_icon()
        if self.hwnd:
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass
