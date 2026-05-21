import threading
import http.server
import socketserver
import json
from wol import send_wol, get_local_mac, get_local_ip, get_computer_name
from device_manager import DeviceManager, is_device_online
from logger import Logger


class WOLWebHandler(http.server.BaseHTTPRequestHandler):
    devices = None
    logger = None
    web_port = 8080

    def log_message(self, format, *args):
        if self.logger:
            self.logger.info(f"Web: {format % args}")

    def do_GET(self):
        if self.path == "/" or self.path == "/wake":
            self._render_wake_page()
        elif self.path.startswith("/api/wol"):
            self._handle_api()
        elif self.path == "/api/devices":
            self._handle_devices()
        elif self.path == "/api/info":
            self._handle_info()
        else:
            self._render_wake_page()

    def do_POST(self):
        if self.path == "/api/wol":
            self._handle_api()
        elif self.path == "/api/devices/add":
            self._handle_add_device()
        elif self.path == "/api/devices/remove":
            self._handle_remove_device()

    def _render_wake_page(self):
        this = get_computer_name()
        this_mac = get_local_mac()
        this_ip = get_local_ip()

        devices = []
        if self.devices:
            devices = self.devices.get_devices()

        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>远程唤醒</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,Microsoft YaHei,sans-serif;background:#f0f2f5;padding:16px;max-width:600px;margin:0 auto}}
.card{{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
h1{{font-size:20px;color:#1a1a2e;margin-bottom:6px}}
p{{color:#666;font-size:14px;line-height:1.5}}
.info-row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0f0f0;font-size:13px}}
.info-row:last-child{{border-bottom:none}}
.info-label{{color:#999}}
.info-value{{color:#333;font-weight:600;font-family:monospace;font-size:12px}}
.btn{{display:inline-block;padding:10px 20px;background:#2A9DFF;color:#fff;border:none;border-radius:8px;font-size:14px;cursor:pointer;text-decoration:none}}
.btn:active{{background:#1a8def}}
.btn-wake{{background:#07C160;font-size:12px;padding:6px 14px}}
.btn-wake:disabled{{background:#ccc;cursor:not-allowed}}
.btn-danger{{background:#ff4757;font-size:11px;padding:4px 10px}}
.btn-copy{{background:#888;font-size:11px;padding:4px 8px;margin-left:6px}}
.device-item{{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f5f5f5}}
.device-item:last-child{{border-bottom:none}}
.device-name{{font-weight:600;color:#333;font-size:14px}}
.device-mac{{color:#999;font-family:monospace;font-size:12px}}
.device-status{{font-size:11px;padding:2px 8px;border-radius:10px;margin-left:6px}}
.status-online{{background:#d4edda;color:#155724}}
.status-offline{{background:#f8d7da;color:#721c24}}
.form-row{{display:flex;gap:8px;margin-bottom:10px}}
.form-row input{{flex:1;padding:8px 12px;border:1px solid #ddd;border-radius:8px;font-size:14px}}
.toast{{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 20px;border-radius:8px;display:none;z-index:999;font-size:13px}}
.empty{{color:#999;text-align:center;padding:16px;font-size:13px}}
</style>
</head>
<body>

<div class="card">
<h1>远程唤醒</h1>
<p>手机/电脑在同一局域网内即可唤醒目标设备</p>
</div>

<div class="card">
<h2 style="font-size:15px;margin-bottom:10px">本设备信息</h2>
<div class="info-row"><span class="info-label">名称</span><span class="info-value">{this}</span></div>
<div class="info-row"><span class="info-label">MAC</span><span class="info-value" id="myMac">{this_mac}</span></div>
<div class="info-row"><span class="info-label">IP</span><span class="info-value">{this_ip}</span></div>
</div>

<div class="card">
<h2 style="font-size:15px;margin-bottom:10px">设备列表</h2>
<div id="deviceList"></div>
</div>

<div class="card">
<h2 style="font-size:15px;margin-bottom:10px">添加设备</h2>
<div class="form-row"><input type="text" id="devName" placeholder="设备名称（如：客厅电脑）"></div>
<div class="form-row"><input type="text" id="devMac" placeholder="MAC 地址（如：AA:BB:CC:DD:EE:FF）"></div>
<div class="form-row"><input type="text" id="devIp" placeholder="IP 地址（可选，如：192.168.1.100）"></div>
<button class="btn" onclick="addDevice()">添加</button>
</div>

<div class="toast" id="toast"></div>

<script>
var API = '/api';
function showToast(msg, dur){{
  var t=document.getElementById('toast');
  t.textContent=msg;
  t.style.display='block';
  setTimeout(function(){{t.style.display='none'}}, dur||2000);
}}
function wake(mac,name){{
  fetch(API+'/wol',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{mac:mac}})}})
  .then(function(r){{return r.json()}})
  .then(function(d){{
    if(d.ok){{showToast('唤醒信号已发送到 '+name)}}
    else{{showToast('发送失败')}}
  }}).catch(function(){{showToast('网络错误')}});
}}
function addDevice(){{
  var n=document.getElementById('devName').value.trim();
  var m=document.getElementById('devMac').value.trim();
  var i=document.getElementById('devIp').value.trim();
  if(!n||!m){{showToast('请填写名称和MAC');return}}
  fetch(API+'/devices/add',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{name:n,mac:m,ip:i}})}})
  .then(function(r){{return r.json()}})
  .then(function(d){{
    if(d.ok){{document.getElementById('devName').value='';document.getElementById('devMac').value='';document.getElementById('devIp').value='';loadDevices()}}
    else{{showToast(d.msg||'添加失败')}}
  }});
}}
function removeDevice(mac){{
  if(!confirm('确定删除？')) return;
  fetch(API+'/devices/remove',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{mac:mac}})}})
  .then(function(r){{return r.json()}})
  .then(function(d){{if(d.ok) loadDevices()}});
}}
function loadDevices(){{
  fetch(API+'/devices').then(function(r){{return r.json()}}).then(function(d){{
    var list = document.getElementById('deviceList');
    if(!d.devices||d.devices.length===0){{
      list.innerHTML='<div class="empty">暂无设备，请在下方添加</div>';
      return;
    }}
    var html='';
    d.devices.forEach(function(dev){{
      var status = dev.online ? '<span class="device-status status-online">已开机</span>' : '<span class="device-status status-offline">关机</span>';
      var btnDisabled = dev.online ? 'disabled' : '';
      html += '<div class="device-item">' +
        '<div><div class="device-name">'+dev.name+status+'</div>' +
        '<div class="device-mac">'+dev.mac+'</div></div>' +
        '<div>' +
        '<button class="btn btn-wake" onclick="wake(\\''+dev.mac+'\\',\\''+dev.name+'\\')" '+btnDisabled+'>唤醒</button>' +
        '<button class="btn btn-danger" onclick="removeDevice(\\''+dev.mac+'\\')">删除</button>' +
        '</div></div>';
    }});
    list.innerHTML = html;
  }});
}}
function copyMac(){{
  navigator.clipboard.writeText(document.getElementById('myMac').innerText).then(function(){{showToast('MAC已复制')}});
}}
document.getElementById('myMac').style.cursor='pointer';
document.getElementById('myMac').title='点击复制';
document.getElementById('myMac').addEventListener('click',copyMac);
loadDevices();
setInterval(loadDevices, 10000);
</script>
</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _handle_api(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            mac = body.get("mac", "")
            if mac and send_wol(mac):
                self._json({"ok": True, "msg": f"WOL sent to {mac}"})
            else:
                self._json({"ok": False, "msg": "Failed"})
        except Exception as e:
            self._json({"ok": False, "msg": str(e)})

    def _handle_devices(self):
        devices = []
        if self.devices:
            devices = self.devices.get_devices()
            for d in devices:
                d["online"] = is_device_online(d.get("ip", ""), 1)
        self._json({"devices": devices})

    def _handle_add_device(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            name = body.get("name", "").strip()
            mac = body.get("mac", "").strip()
            ip = body.get("ip", "").strip()
            if not name or not mac:
                self._json({"ok": False, "msg": "名称和MAC不能为空"})
                return
            if self.devices and self.devices.add_device(name, mac, ip):
                self._json({"ok": True})
            else:
                self._json({"ok": False, "msg": "设备已存在"})
        except Exception as e:
            self._json({"ok": False, "msg": str(e)})

    def _handle_remove_device(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            mac = body.get("mac", "").strip()
            if self.devices and self.devices.remove_device(mac):
                self._json({"ok": True})
            else:
                self._json({"ok": False, "msg": "删除失败"})
        except Exception as e:
            self._json({"ok": False, "msg": str(e)})

    def _handle_info(self):
        self._json({
            "name": get_computer_name(),
            "mac": get_local_mac(),
            "ip": get_local_ip(),
        })

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


class WOLWebServer:
    def __init__(self, port: int = 8080, device_manager=None, logger=None):
        self.port = port
        self.device_manager = device_manager
        self.logger = logger or Logger()
        self._running = False
        self._thread = None
        self._server = None

    def start(self):
        if self._running:
            return
        self._running = True

        WOLWebHandler.devices = self.device_manager
        WOLWebHandler.logger = self.logger
        WOLWebHandler.web_port = self.port

        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self.logger.info(f"WOL Web Server started at http://localhost:{self.port}")

    def stop(self):
        self._running = False
        if self._server:
            self._server.shutdown()
        self.logger.info("WOL Web Server stopped")

    def _serve(self):
        try:
            self._server = socketserver.TCPServer(("", self.port), WOLWebHandler)
            self._server.allow_reuse_address = True
            while self._running:
                self._server.handle_request()
        except Exception as e:
            self.logger.error(f"WOL Web Server error: {e}")
