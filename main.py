import tkinter as tk
from tkinter import messagebox, ttk
import os
import sys
import ctypes
import threading
from pathlib import Path
from PIL import Image, ImageTk

from config_manager import ConfigManager, DEFAULT_CONFIG
from daemon import ConnectionDaemon
from autostart import is_autostart_enabled, enable_autostart, disable_autostart
from wol import send_wol, WOLServer, get_local_mac, get_computer_name, get_local_ip
from logger import Logger
from icon_generator import generate_icon
from tray import SystemTray
from device_manager import DeviceManager, enable_wol_adapter, is_device_online
from web_wol import WOLWebServer


class CampusNetworkApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("自动校园网连接")
        self.root.geometry("680x900")
        self.root.minsize(600, 600)

        self.config = ConfigManager()
        self.logger = Logger()
        self.daemon = None
        self.wol_server = None
        self.tray = None
        self.device_mgr = DeviceManager()
        self.web_server = None

        self._setup_icon()
        self._setup_styles()
        self._create_widgets()
        self._load_config()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_icon(self):
        try:
            png_path = generate_icon()
            ico_path = str(Path(__file__).parent / "app_icon.ico")
            self.app_icon = ImageTk.PhotoImage(file=png_path)
            self.root.iconphoto(True, self.app_icon)
            if os.path.exists(ico_path):
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CampusNetwork.AutoDial")
                self.root.iconbitmap(ico_path)
        except Exception:
            pass

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Header.TLabel", font=("Microsoft YaHei", 16, "bold"))
        style.configure("Info.TLabel", font=("Microsoft YaHei", 9))
        style.configure("Action.TButton", font=("Microsoft YaHei", 11, "bold"))
        style.configure("Warn.TLabel", font=("Microsoft YaHei", 9), foreground="#FF6600")
        style.configure("Green.TLabel", font=("Microsoft YaHei", 9), foreground="#07C160")

    def _create_widgets(self):
        main = ttk.Frame(self.root, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(main, highlightthickness=0)
        sb = ttk.Scrollbar(main, orient="vertical", command=canvas.yview)
        self.sf = ttk.Frame(canvas)

        self.sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.sf, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._build(self.sf)

    def _build(self, parent):
        parent.columnconfigure(0, weight=1)

        ttk.Label(parent, text="自动校园网连接", style="Header.TLabel").grid(row=0, column=0, pady=(0, 15), sticky="w")

        self._conn_config(parent)
        self._work_time(parent)
        self._retry_config(parent)
        self._autostart(parent)
        self._wol_section(parent)
        self._wol_guide(parent)
        self._wol_phone(parent)
        self._actions(parent)
        self._status_bar(parent)

    def _conn_config(self, parent):
        f = ttk.LabelFrame(parent, text="连接配置", padding=12)
        f.grid(row=1, column=0, pady=8, sticky="ew")
        f.columnconfigure(1, weight=1)

        self.conn_var = tk.StringVar(value="宽带连接")
        self._add_row(f, 0, "连接名称:", self.conn_var, "例: 宽带连接")

        self.user_var = tk.StringVar()
        self._add_row(f, 1, "用户名:", self.user_var, "例: 13800138000@cmcc")

        self.pass_var = tk.StringVar()
        self.pass_entry = ttk.Entry(f, textvariable=self.pass_var, show="*")
        ttk.Label(f, text="密码:").grid(row=2, column=0, sticky="w", pady=5)
        self.pass_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=5)
        ttk.Label(f, text="例: yourpassword", style="Warn.TLabel").grid(row=2, column=2, padx=(5, 0))

        self.show_pass = tk.BooleanVar()
        ttk.Checkbutton(f, text="显示密码", variable=self.show_pass,
                        command=lambda: self.pass_entry.config(show="" if self.show_pass.get() else "*")).grid(row=3, column=1, sticky="w", padx=(10, 0))

    def _add_row(self, parent, row, label, var, example):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=5)
        ttk.Label(parent, text=example, style="Warn.TLabel").grid(row=row, column=2, padx=(5, 0))

    def _work_time(self, parent):
        f = ttk.LabelFrame(parent, text="工作时间", padding=12)
        f.grid(row=2, column=0, pady=8, sticky="ew")

        self.wstart = tk.StringVar(value="06:00")
        self.wend = tk.StringVar(value="22:30")

        ttk.Label(f, text="开始:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(f, textvariable=self.wstart, width=10).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
        ttk.Label(f, text="结束:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(f, textvariable=self.wend, width=10).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)

    def _retry_config(self, parent):
        f = ttk.LabelFrame(parent, text="重试设置", padding=12)
        f.grid(row=3, column=0, pady=8, sticky="ew")

        self.rlimit = tk.StringVar(value="30")
        self.rinterval = tk.StringVar(value="10")
        self.cinterval = tk.StringVar(value="30")
        self.sinterval = tk.StringVar(value="600")

        self._add_row(f, 0, "最大重试次数:", self.rlimit, "例: 30")
        self._add_row(f, 1, "重试间隔(秒):", self.rinterval, "例: 10")
        self._add_row(f, 2, "检查间隔(秒):", self.cinterval, "例: 30")
        self._add_row(f, 3, "休眠间隔(秒):", self.sinterval, "例: 600")

    def _autostart(self, parent):
        f = ttk.LabelFrame(parent, text="开机自启", padding=12)
        f.grid(row=4, column=0, pady=8, sticky="ew")
        self.auto_var = tk.IntVar(value=0)
        tk.Checkbutton(f, text="开机自动启动（后台静默连接）", variable=self.auto_var,
                       selectcolor=self.root.cget("bg"), font=("Microsoft YaHei", 9),
                       indicatoron=True, relief="flat", anchor="w").pack(anchor="w", fill=tk.X)

    def _wol_section(self, parent):
        f = ttk.LabelFrame(parent, text="远程唤醒", padding=12)
        f.grid(row=5, column=0, pady=8, sticky="ew")
        f.columnconfigure(1, weight=1)

        this = self.device_mgr.get_this_computer()
        ttk.Label(f, text="本设备信息:").grid(row=0, column=0, sticky="w", pady=5)
        info = f"名称: {this['name']}\nMAC: {this['mac']}\nIP: {this['ip']}"
        ttk.Label(f, text=info, style="Info.TLabel").grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)

        ttk.Label(f, text="设备列表:").grid(row=1, column=0, sticky="nw", pady=5)
        list_frame = ttk.Frame(f)
        list_frame.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)

        cols = ("name", "mac", "status", "action")
        self.wol_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=4)
        self.wol_tree.heading("name", text="设备名称")
        self.wol_tree.heading("mac", text="MAC 地址")
        self.wol_tree.heading("status", text="状态")
        self.wol_tree.heading("action", text="操作")
        self.wol_tree.column("name", width=100)
        self.wol_tree.column("mac", width=120)
        self.wol_tree.column("status", width=60)
        self.wol_tree.column("action", width=50)
        self.wol_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=1, column=2, padx=5)
        ttk.Button(btn_frame, text="添加设备", command=self._wol_add_dialog).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="刷新状态", command=self._refresh_wol_list).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Web 管理", command=self._open_web).pack(fill=tk.X, pady=2)

        self._refresh_wol_list()

    def _wol_guide(self, parent):
        f = ttk.LabelFrame(parent, text="被其他设备唤醒（一键设置）", padding=12)
        f.grid(row=6, column=0, pady=8, sticky="ew")

        step_frame = ttk.Frame(f)
        step_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(step_frame, text="第 1 步（自动完成）：", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(0, 2))
        ttk.Label(step_frame, text="点击下方按钮，软件自动配置网卡 WOL 功能", style="Info.TLabel").pack(anchor="w")

        btn_frame = ttk.Frame(f)
        btn_frame.pack(fill=tk.X, pady=5)
        self.wol_config_btn = ttk.Button(btn_frame, text="一键配置网卡 WOL", command=self._do_wol_config)
        self.wol_config_btn.pack(side=tk.LEFT)
        self.wol_config_status = ttk.Label(btn_frame, text="", style="Green.TLabel")
        self.wol_config_status.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(f, text="第 2 步（需要动手）：", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(8, 2))
        manual = ("重启电脑 → 开机时连续按 F2 或 Del 键 → 进入 BIOS\n"
                  "找到 Wake on LAN / Power on by PCIE → 设为 Enabled → 保存退出")
        ttk.Label(f, text=manual, style="Warn.TLabel").pack(anchor="w")

        copy_frame = ttk.Frame(f)
        copy_frame.pack(fill=tk.X, pady=(10, 0))
        mac = get_local_mac()
        ttk.Label(copy_frame, text=f"本机 MAC: {mac}  （点击复制）",
                  style="Info.TLabel", cursor="hand1").pack(side=tk.LEFT)
        copy_frame.bind("<Button-1>", lambda e: self._copy_mac(mac))

    def _wol_phone(self, parent):
        f = ttk.LabelFrame(parent, text="手机如何唤醒本电脑？", padding=12)
        f.grid(row=7, column=0, pady=8, sticky="ew")

        ttk.Label(f, text="方法一：浏览器唤醒（推荐）", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(0, 4))
        steps_browser = (
            "1. 手机和电脑连同一个 WiFi\n"
            "2. 打开浏览器，访问 http://本电脑IP:8080/wake\n"
            "   （本电脑 IP 见上方「本设备信息」）\n"
            "3. 网页上点击「唤醒」按钮即可"
        )
        ttk.Label(f, text=steps_browser, style="Info.TLabel").pack(anchor="w")

        ttk.Label(f, text="方法二：WOL App 唤醒", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(12, 4))
        steps_app = (
            "1. 手机安装 WOL App（应用商店搜索 Wake On Lan）\n"
            "2. 添加设备，输入本电脑 MAC 地址（见上方，点击可复制）\n"
            "3. 在 App 中点击该设备，即可唤醒"
        )
        ttk.Label(f, text=steps_app, style="Info.TLabel").pack(anchor="w")

        ttk.Label(f, text="外网唤醒（不在同一网络）", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w", pady=(12, 4))
        steps_remote = (
            "路由器设置端口转发：UDP 55555 → 本电脑IP:55555\n"
            "手机通过公网 IP 或 DDNS 域名发送唤醒"
        )
        ttk.Label(f, text=steps_remote, style="Warn.TLabel").pack(anchor="w")

    def _do_wol_config(self):
        self.wol_config_btn.config(state=tk.DISABLED, text="配置中...")
        self.root.update()

        def run_config():
            ok, msg = enable_wol_adapter()
            self.root.after(0, self._on_wol_config_done, ok, msg)

        threading.Thread(target=run_config, daemon=True).start()

    def _on_wol_config_done(self, ok, msg):
        self.wol_config_btn.config(state=tk.NORMAL, text="一键配置网卡 WOL")
        if ok:
            self.wol_config_status.config(text="配置成功！", foreground="#07C160")
            messagebox.showinfo("成功", "网卡 WOL 已配置完成！\n\n请继续第 2 步：进入 BIOS 开启 Wake on LAN")
            self.logger.info("WOL 网卡配置成功")
        else:
            self.wol_config_status.config(text="配置失败", foreground="#FF4757")
            messagebox.showerror("失败", f"配置失败：{msg}\n\n请以管理员身份运行本软件后重试")

    def _copy_mac(self, mac):
        self.root.clipboard_clear()
        self.root.clipboard_append(mac)
        messagebox.showinfo("已复制", f"MAC 地址已复制：{mac}")

    def _open_web(self):
        import webbrowser
        url = f"http://localhost:8080/wake"
        webbrowser.open(url)

    def _refresh_wol_list(self):
        for i in self.wol_tree.get_children():
            self.wol_tree.delete(i)
        for d in self.device_mgr.get_devices():
            ip = d.get("ip", "")
            online = is_device_online(ip, 1) if ip else False
            status_text = "在线" if online else "关机"
            action_text = "唤醒" if not online else "已醒"
            self.wol_tree.insert("", tk.END, values=(d["name"], d["mac"], status_text, action_text),
                                 tags=(d["mac"], "online" if online else "offline"))
        self.wol_tree.bind("<Button-1>", self._wol_tree_click)
        self.wol_tree.bind("<Double-1>", self._wol_wake_selected)

    def _wol_tree_click(self, event):
        item = self.wol_tree.identify_row(event.y)
        if item:
            col = self.wol_tree.identify_column(event.x)
            if col == "#4":
                tags = self.wol_tree.item(item, "tags")
                if tags and "online" in tags:
                    name = self.wol_tree.item(item, "values")[0]
                    messagebox.showinfo("提示", f"设备「{name}」已处于唤醒状态")
                else:
                    mac = self.wol_tree.item(item, "tags")[0]
                    self._wol_wake(mac)

    def _wol_wake_selected(self, event):
        item = self.wol_tree.selection()
        if item:
            tags = self.wol_tree.item(item[0], "tags")
            mac = tags[0] if tags else None
            if mac:
                if tags and "online" in tags:
                    name = self.wol_tree.item(item[0], "values")[0]
                    messagebox.showinfo("提示", f"设备「{name}」已处于唤醒状态")
                else:
                    self._wol_wake(mac)

    def _wol_wake(self, mac):
        if not mac:
            return
        if send_wol(mac):
            messagebox.showinfo("成功", f"唤醒信号已发送到 {mac}")
            self.logger.info(f"WOL 唤醒信号已发送到 {mac}")
            self.root.after(3000, self._refresh_wol_list)
        else:
            messagebox.showerror("失败", "唤醒信号发送失败")

    def _wol_add_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("添加唤醒设备")
        dlg.geometry("420x250")
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text="设备名称:").grid(row=0, column=0, sticky="w", padx=15, pady=10)
        name_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=name_var, width=25).grid(row=0, column=1, padx=5, pady=10)

        ttk.Label(dlg, text="MAC 地址:").grid(row=1, column=0, sticky="w", padx=15, pady=5)
        mac_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=mac_var, width=25).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dlg, text="IP 地址（可选）:").grid(row=2, column=0, sticky="w", padx=15, pady=5)
        ip_var = tk.StringVar()
        ttk.Entry(dlg, textvariable=ip_var, width=25).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(dlg, text="例: AA:BB:CC:DD:EE:FF", style="Warn.TLabel").grid(row=3, column=1, sticky="w", padx=5)

        def do_add():
            name = name_var.get().strip()
            mac = mac_var.get().strip()
            ip = ip_var.get().strip()
            if not name or not mac:
                messagebox.showwarning("提示", "请填写名称和MAC")
                return
            if self.device_mgr.add_device(name, mac, ip):
                self._refresh_wol_list()
                dlg.destroy()
            else:
                messagebox.showwarning("提示", "该设备已存在")

        ttk.Button(dlg, text="添加", command=do_add).grid(row=4, column=1, sticky="e", padx=5, pady=15)

    def _actions(self, parent):
        f = ttk.Frame(parent)
        f.grid(row=8, column=0, pady=15, sticky="ew")
        f.columnconfigure((0, 1, 2), weight=1)

        self.save_btn = ttk.Button(f, text="保存并最小化到托盘", command=self._save_and_start,
                                   style="Action.TButton")
        self.save_btn.grid(row=0, column=0, padx=5, sticky="ew")

        self.stop_btn = ttk.Button(f, text="停止", command=self._stop_daemon,
                                   style="Action.TButton", state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5, sticky="ew")

        ttk.Button(f, text="日志", command=self._show_logs).grid(row=0, column=2, padx=5, sticky="ew")

    def _status_bar(self, parent):
        f = ttk.LabelFrame(parent, text="状态", padding=10)
        f.grid(row=9, column=0, pady=8, sticky="ew")
        self.status_var = tk.StringVar(value="未启动")
        ttk.Label(f, textvariable=self.status_var, style="Info.TLabel").pack(anchor="w")

    def _load_config(self):
        c = self.config.get_config()
        self.conn_var.set(c.get("connection_name", "宽带连接"))
        self.user_var.set(c.get("username", ""))
        self.pass_var.set(c.get("password", ""))
        self.wstart.set(c.get("work_time_start", "06:00"))
        self.wend.set(c.get("work_time_end", "22:30"))
        self.rlimit.set(str(c.get("retry_limit", 30)))
        self.rinterval.set(str(c.get("retry_interval", 10)))
        self.cinterval.set(str(c.get("check_interval", 30)))
        self.sinterval.set(str(c.get("sleep_interval", 600)))
        self.auto_var.set(1 if is_autostart_enabled() else 0)
        self._detect_autostart_mode()

    def _detect_autostart_mode(self):
        if "--autostart" not in sys.argv:
            return
        c = self.config.get_config()
        if c.get("username") and c.get("password"):
            self.root.withdraw()
            self.root.after(500, lambda: self._start_daemon(c))
            self.save_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_var.set("运行中 - 开机自启（后台）")
            self.logger.info("开机自启模式：后台静默启动")
            self.root.after(1000, self._create_tray_only)

    def _create_tray_only(self):
        if not self.tray and self.daemon:
            self.tray = SystemTray(self.daemon, self.logger, self.config, self)
            self.tray.start()

    def _save_config(self):
        c = {
            "connection_name": self.conn_var.get().strip(),
            "username": self.user_var.get().strip(),
            "password": self.pass_var.get().strip(),
            "work_time_start": self.wstart.get().strip(),
            "work_time_end": self.wend.get().strip(),
            "retry_limit": int(self.rlimit.get() or 30),
            "retry_interval": int(self.rinterval.get() or 10),
            "check_interval": int(self.cinterval.get() or 30),
            "sleep_interval": int(self.sinterval.get() or 600),
        }
        self.config.save_config(c)
        return c

    def _save_and_start(self):
        c = self._save_config()
        if not c["connection_name"] or not c["username"] or not c["password"]:
            messagebox.showwarning("提示", "请填写连接名称、用户名和密码")
            return

        if self.auto_var.get():
            exe_path = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
            enable_autostart(exe_path)
        else:
            disable_autostart()

        self._start_daemon(c)
        self.root.withdraw()

    def _start_daemon(self, c):
        self.daemon = ConnectionDaemon(c, self.logger, self._on_status)
        self.daemon.start()

        self.wol_server = WOLServer(port=55555, logger=self.logger)
        self.wol_server.start()

        self.web_server = WOLWebServer(port=8080, device_manager=self.device_mgr, logger=self.logger)
        self.web_server.start()

        self.tray = SystemTray(self.daemon, self.logger, self.config, self)
        self.tray.start()

        self.save_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("运行中 - 已最小化到托盘")
        self.logger.info("守护进程已启动")

    def _stop_daemon(self):
        if self.tray:
            self.tray.stop()
            self.tray = None
        if self.daemon:
            self.daemon.stop()
            self.daemon = None
        if self.wol_server:
            self.wol_server.stop()
            self.wol_server = None
        if self.web_server:
            self.web_server.stop()
            self.web_server = None

        self.save_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("已停止")
        self.logger.info("守护进程已停止")
        self.root.deiconify()

    def _on_status(self, status, msg):
        self.root.after(0, lambda: self.status_var.set(f"{status}: {msg}"))

    def _on_closing(self):
        if self.daemon and self.daemon.is_running():
            self.root.withdraw()
        else:
            self.root.destroy()

    def quit(self):
        self.root.quit()

    def _show_logs(self):
        w = tk.Toplevel(self.root)
        w.title("运行日志")
        w.geometry("700x500")

        tb = ttk.Frame(w)
        tb.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(tb, text="刷新", command=lambda: self._refresh_log(t)).pack(side=tk.LEFT, padx=2)
        ttk.Button(tb, text="清空", command=lambda: self._clear_log(t)).pack(side=tk.LEFT, padx=2)

        tf = ttk.Frame(w)
        tf.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        t = tk.Text(tf, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 10))
        sb = ttk.Scrollbar(tf, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        t.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._refresh_log(t)

    def _refresh_log(self, tw):
        logs = self.logger.get_recent_logs(500)
        tw.config(state=tk.NORMAL)
        tw.delete(1.0, tk.END)
        for l in logs:
            tw.insert(tk.END, l + "\n")
        tw.config(state=tk.DISABLED)
        tw.see(tk.END)

    def _clear_log(self, tw):
        self.logger.clear_logs()
        self._refresh_log(tw)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = CampusNetworkApp()
    app.run()
