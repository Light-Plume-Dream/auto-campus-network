import struct
import socket
import json
import threading
import subprocess
import uuid
from pathlib import Path
from logger import Logger


WOL_PORT = 9


def create_magic_packet(mac: str) -> bytes:
    mac = mac.replace(":", "").replace("-", "").upper()
    if len(mac) != 12:
        raise ValueError("Invalid MAC address")
    mac_bytes = bytes.fromhex(mac)
    packet = b"\xff" * 6
    packet += mac_bytes * 16
    return packet


def send_wol(mac: str, broadcast_ip: str = "255.255.255.255", port: int = WOL_PORT) -> bool:
    try:
        packet = create_magic_packet(mac)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (broadcast_ip, port))
        return True
    except Exception as e:
        print(f"WOL send error: {e}")
        return False


def get_local_mac() -> str:
    try:
        mac = uuid.getnode()
        return ":".join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
    except Exception:
        return ""


def get_computer_name() -> str:
    import platform
    return platform.node()


def get_local_ip() -> str:
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception:
        return ""


class WOLServer:
    def __init__(self, port: int = 55555, logger=None):
        self.port = port
        self.logger = logger or Logger()
        self._running = False
        self._server_thread = None
        self._socket = None
        self._callback = None

    def set_callback(self, callback):
        self._callback = callback

    def start(self):
        if self._running:
            return
        self._running = True
        self._server_thread = threading.Thread(target=self._serve, daemon=True)
        self._server_thread.start()
        self.logger.info(f"WOL Server started on port {self.port}")

    def stop(self):
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
        self.logger.info("WOL Server stopped")

    def _serve(self):
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(("", self.port))
            self._socket.settimeout(1.0)

            self.logger.info(f"WOL Server listening on port {self.port}")

            while self._running:
                try:
                    data, addr = self._socket.recvfrom(1024)
                    if data == b"WOL_TRIGGER":
                        self.logger.info(f"WOL trigger received from {addr}")
                        if self._callback:
                            self._callback()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        self.logger.error(f"WOL Server error: {e}")
        except Exception as e:
            self.logger.error(f"WOL Server failed to start: {e}")
