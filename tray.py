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
        self._next_id = 1000
        self._menu_actions = {}
        self._tk_hwnd = None

    def _find_tkinter_hwnd(self):
        try:
            if self.app_root and hasattr(self.app_root, 'root'):
                self._tk_hwnd = self.app_root.root.winfo_id()
                return self._tk_hwnd
        except Exception:
            pass
        return None

    def _load_icon(self):
        ico_paths = []
        
        if getattr(sys, "frozen", False):
            ico_paths.append(os.path.join(sys._MEIPASS, "app_icon.ico"))
        
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

        if getattr(sys, "frozen", False):
            try:
                hmod = win32api.GetModuleHandle(None)
                hicon = win32gui.LoadIcon(hmod, 1)
                if hicon:
                    return hicon
            except Exception:
                pass

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

        try:
            hmod = win32api.GetModuleHandle(None)
            return win32gui.LoadIcon(hmod, win32con.IDI_APPLICATION)
        except Exception:
            return 0

    def _add_menu_item(self, menu, text, action):
        item_id = self._next_id
        self._next_id += 1
        self._menu_actions[item_id] = action
        win32gui.AppendMenu(menu, win32con.MF_STRING, item_id, text)
        return item_id

    def _on_menu_select(self, item_id):
        action = self._menu_actions.get(item_id)
        if action:
            try:
                action()
            except Exception as e:
                self.logger.error(f"菜单回调错误: {e}")

    def _show_menu(self):
        menu = win32gui.CreatePopupMenu()
        self._menu_actions = {}
        self._next_id = 1000

        self._add_menu_item(menu, "显示窗口", self._show_window_direct)
        self._add_menu_item(menu, "查看日志", self._show_logs)

        if self.daemon.is_running():
            label = "恢复连接" if self.daemon.is_paused() else "暂停连接"
        else:
            label = "启动连接"
        self._add_menu_item(menu, label, self._toggle_connection)

        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        self._add_menu_item(menu, "退出", self._quit)

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        
        cmd = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RETURNCMD | win32con.TPM_RIGHTBUTTON,
            pos[0], pos[1],
            0, self.hwnd, None
        )
        
        if cmd:
            self._on_menu_select(cmd)
        
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

    def _show_window_direct(self):
        try:
            if self.app_root and hasattr(self.app_root, 'root'):
                root = self.app_root.root
                root.after(0, self._do_show_window)
        except Exception as e:
            self.logger.error(f"显示窗口失败: {e}")

    def _do_show_window(self):
        try:
            root = self.app_root.root
            root.deiconify()
            root.lift()
            root.attributes('-topmost', True)
            root.after(100, lambda: root.attributes('-topmost', False))
            root.focus_force()
        except Exception as e:
            self.logger.error(f"显示窗口失败: {e}")

    def _show_logs(self):
        try:
            if self.app_root:
                self.app_root.after(0, self.app_root._show_logs)
        except Exception as e:
            self.logger.error(f"显示日志失败: {e}")

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
        try:
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
        except Exception as e:
            self.logger.error(f"退出失败: {e}")

    def start(self):
        self._thread = threading.Thread(target=self._run_tray, daemon=True)
        self._thread.start()

    def _run_tray(self):
        self._running = True
        self._find_tkinter_hwnd()

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

    def _icon_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            if lparam in (win32con.WM_RBUTTONUP, win32con.WM_CONTEXTMENU):
                self._show_menu()
            elif lparam == win32con.WM_LBUTTONDBLCLK:
                self._show_window_direct()
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

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
