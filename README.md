# 自动校园网连接

> 一个 Windows 校园网宽带自动连接守护程序，支持断线自动重连、系统托盘、开机自启、远程唤醒 (WOL) 等功能。

## 功能特性

- **断线自动重连** - 实时检测宽带连接状态，断开后自动拨号
- **工作时间控制** - 可设置工作时间段，非工作时间自动休眠
- **系统托盘** - 最小化到托盘，右键菜单控制暂停/恢复/退出
- **开机自启** - 一键设置开机自动启动
- **远程唤醒 (WOL)** - 手机/电脑远程唤醒目标设备，支持 Web 管理页面
- **设备管理** - 添加/删除唤醒设备，实时检测在线状态
- **日志管理** - 记录运行日志，支持查看和清空

## 安装

### 方式一：使用发布包（推荐）

1. 下载 [发布包](./发布包/) 文件夹
2. 运行 `安装程序.bat`
3. 双击桌面快捷方式即可使用

### 方式二：从源码运行

```bash
# 1. 安装 Python 3.8+（需要包含 Tkinter）
# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

### 打包为 exe

```bash
# Windows 下执行
build.bat
```

打包完成后，`dist/` 目录下会生成 `自动校园网连接.exe`

## 使用

1. 打开软件，填写宽带连接信息（连接名称、用户名、密码）
2. 可选：勾选「开机自动启动」
3. 点击「保存并最小化到托盘」
4. 软件将在后台运行，自动检测并重连

### 远程唤醒

**被其他设备唤醒**：
1. 点击「一键配置网卡 WOL」
2. 重启电脑，进入 BIOS 开启 Wake on LAN
3. 其他设备通过 MAC 地址发送唤醒信号

**唤醒其他设备**：
1. 添加设备的名称和 MAC 地址
2. 点击「唤醒」按钮
3. 已在线设备会显示提示

**手机唤醒**：
- 浏览器：手机访问 `http://电脑IP:8080/wake`
- App：安装 Wake On Lan 类 App，输入 MAC 地址

## 项目结构

```
├── main.py               # 主程序入口，UI 界面
├── config_manager.py     # 配置管理（JSON 读写）
├── daemon.py             # 自动连接守护进程
├── tray.py               # 系统托盘管理
├── autostart.py          # 开机自启动（Windows 注册表）
├── wol.py                # WOL 远程唤醒（UDP 魔法包）
├── web_wol.py            # WOL Web 管理页面
├── device_manager.py     # 设备列表管理
├── logger.py             # 日志管理
├── icon_generator.py     # 图标自动生成器
├── requirements.txt      # Python 依赖
└── build.bat             # 一键打包脚本
```

## 技术栈

- **Python 3.8+**
- **Tkinter** - GUI 界面
- **pystray** - 系统托盘
- **Pillow** - 图标处理
- **PyInstaller** - 打包为 exe
- **rasdial** - Windows 宽带拨号

## 注意事项

- 本软件仅适用于 Windows 系统
- 需要管理员权限运行以修改网卡 WOL 配置
- BIOS 中的 Wake on LAN 需要手动开启
- 外网唤醒需要路由器端口转发

## License

MIT License
