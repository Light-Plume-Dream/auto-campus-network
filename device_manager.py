import subprocess
import json
import os
import sys
import threading
from pathlib import Path
from wol import get_local_mac, get_computer_name, get_local_ip


DEFAULT_DEVICES_FILE = "wol_devices.json"


class DeviceManager:
    def __init__(self, devices_path=None):
        if devices_path is None:
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            devices_path = Path(base_dir) / DEFAULT_DEVICES_FILE
        self.devices_path = Path(devices_path)
        self._lock = threading.Lock()

    def get_devices(self) -> list:
        with self._lock:
            if not self.devices_path.exists():
                return []
            try:
                with open(self.devices_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    return []
            except Exception:
                return []

    def save_devices(self, devices: list) -> bool:
        with self._lock:
            try:
                with open(self.devices_path, "w", encoding="utf-8") as f:
                    json.dump(devices, f, indent=4, ensure_ascii=False)
                return True
            except Exception:
                return False

    def add_device(self, name: str, mac: str, ip: str = "", port: int = 55555) -> bool:
        devices = self.get_devices()
        if any(d.get("mac", "").lower() == mac.lower() for d in devices):
            return False
        devices.append({
            "name": name,
            "mac": mac,
            "ip": ip,
            "port": port,
        })
        return self.save_devices(devices)

    def remove_device(self, mac: str) -> bool:
        devices = self.get_devices()
        devices = [d for d in devices if d.get("mac", "").lower() != mac.lower()]
        return self.save_devices(devices)

    def get_device(self, mac: str) -> dict:
        for d in self.get_devices():
            if d.get("mac", "").lower() == mac.lower():
                return d
        return {}

    def get_this_computer(self) -> dict:
        return {
            "name": get_computer_name(),
            "mac": get_local_mac(),
            "ip": get_local_ip(),
        }


def is_device_online(ip: str, timeout: int = 1) -> bool:
    if not ip:
        return False
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout * 1000), ip],
            capture_output=True,
            timeout=timeout + 2,
        )
        return b"TTL=" in result.stdout or b"ttl=" in result.stdout
    except Exception:
        return False


def enable_wol_adapter():
    ps_script = r"""
    $ErrorActionPreference = "SilentlyContinue"
    $adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' }
    $results = @()
    foreach ($adapter in $adapters) {
        $adapterName = $adapter.Name
        $path = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
        $folders = Get-ChildItem $path
        foreach ($folder in $folders) {
            $driverDesc = Get-ItemProperty -Path $folder.PSPath -Name "DriverDesc" -ErrorAction SilentlyContinue
            if ($driverDesc -and $driverDesc.DriverDesc) {
                Set-ItemProperty -Path $folder.PSPath -Name "*WakeOnMagicPacket" -Value "1"
                Set-ItemProperty -Path $folder.PSPath -Name "*WakeOnPattern" -Value "1"
                Set-ItemProperty -Path $folder.PSPath -Name "*WakeOnLink" -Value "1"
                $results += "设置 $adapterName 网卡 WOL: 成功"
            }
        }
    }
    $nics = Get-WmiObject -Class MSPower_DeviceEnable -Namespace root\wmi
    foreach ($nic in $nics) { $nic.enable = $true; $nic.Put() | Out-Null }
    $results += "电源管理设置: 成功"
    $results | ForEach-Object { Write-Output $_ }
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)
