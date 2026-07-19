import sys
import os
import time
import threading
import ctypes
import webbrowser
import hid
from PIL import Image, ImageDraw, ImageFont
import pystray
import winreg

APP_NAME = "Attack Shark Battery Tray"
APP_VERSION = "1.2.0"
PROJECT_URL = "https://github.com/subok911/attack-shark-battery-tray"
MUTEX_NAME = "AttackSharkBatteryTray_SingleInstance"
ERROR_ALREADY_EXISTS = 183
_mutex_handle = None

# USB VID for Attack Shark / Beken OEM
VID = 0x1d57

# Dictionary of supported Product IDs mapping to (Model Name, Connection Mode)
SUPPORTED_DEVICES = {
    # Attack Shark X11
    0xfa60: ("Attack Shark X11", "wireless"),
    0xfa55: ("Attack Shark X11", "wired"),
    
    # Attack Shark R1
    0xfa61: ("Attack Shark R1", "wired"),
    
    # Attack Shark X3
    0xfa50: ("Attack Shark X3", "wired"),
    
    # Attack Shark X6
    0xfa62: ("Attack Shark X6", "wireless"),
    0xfa56: ("Attack Shark X6", "wired"),
}

# Helper functions for Windows startup registry keys
def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "AttackSharkBatteryTray")
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

def set_startup(enabled):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    name = "AttackSharkBatteryTray"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if enabled:
            # Check if running as compiled executable or python script
            if getattr(sys, 'frozen', False):
                cmd = f'"{sys.executable}"'
            else:
                script_path = os.path.abspath(sys.argv[0])
                # Use pythonw.exe to run silently without command window
                pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
                cmd = f'"{pythonw_path}" "{script_path}"'
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error setting registry startup: {e}")
        return False

class BatteryTrayApp:
    def __init__(self):
        self.icon = None
        self.running = True
        self.device = None
        self.last_battery = -1
        self.status = "disconnected" # "connected", "waiting", "charging", "disconnected"
        self.current_model = "Attack Shark X11" # Default fallback name
        
        # Start background polling thread
        self.poll_thread = threading.Thread(target=self.poll_loop, daemon=True)
        
    def create_image(self, text, text_color):
        # Create a 64x64 image for the system tray icon (fully transparent background)
        width, height = 64, 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Try loading Arial Bold for high visibility when downscaled in the taskbar
        font = None
        try:
            # Use extra large font sizes (54 for 2 chars, 34 for 3 chars) so the number fills the tray space
            font = ImageFont.truetype("arialbd.ttf", 54 if len(text) <= 2 else 34)
        except IOError:
            try:
                font = ImageFont.truetype("arial.ttf", 54 if len(text) <= 2 else 34)
            except IOError:
                font = ImageFont.load_default()
            
        # Draw text centered exactly using bounding box coordinates
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top
        
        x = (width - text_width) / 2 - left
        y = (height - text_height) / 2 - top
            
        draw.text((x, y), text, fill=text_color, font=font)
        return image

    def get_icon_data(self):
        if self.status == "disconnected":
            return self.create_image("??", (150, 150, 150))
        elif self.status == "waiting":
            return self.create_image("--", (150, 150, 150))
        elif self.status == "charging":
            return self.create_image("Chg", (52, 152, 219)) # Blue
        else:
            # Connected, use percentage
            pct = self.last_battery
            if pct >= 50:
                color = (46, 204, 113) # Green
            elif pct >= 20:
                color = (230, 126, 34) # Orange
            else:
                color = (231, 76, 60) # Red
            return self.create_image(str(pct), color)

    def update_tray(self):
        if not self.icon:
            return
        
        # Update icon image
        self.icon.icon = self.get_icon_data()
        
        # Update tooltip
        model = self.current_model or "Attack Shark Mouse"
        if self.status == "disconnected":
            self.icon.title = f"{model}: Disconnected"
        elif self.status == "waiting":
            self.icon.title = f"{model}: Move the mouse to read its battery"
        elif self.status == "charging":
            self.icon.title = f"{model}: Charging/Wired"
        else:
            self.icon.title = f"{model}: {self.last_battery}%"

    def find_device_path(self):
        # Scan for any device matching the Attack Shark/Beken Vendor ID (0x1d57),
        # matching interface 2 and usage page 10.
        for d in hid.enumerate():
            if d['vendor_id'] == VID and d['interface_number'] == 2 and d['usage_page'] == 10:
                pid = d['product_id']
                
                # Check if it's in our known supported devices list
                if pid in SUPPORTED_DEVICES:
                    model_name, mode = SUPPORTED_DEVICES[pid]
                    return d['path'], mode, model_name
                
                # Fallback: treat it generically
                prod_string = str(d.get('product_string', '')).lower()
                # Guess mode based on product string
                if "wired" in prod_string:
                    mode = "wired"
                elif "wireless" in prod_string or "receiver" in prod_string or "dongle" in prod_string:
                    mode = "wireless"
                else:
                    # Default to wireless as most people use the tray app for wireless mode
                    mode = "wireless"
                
                # Use product string or format generic name
                model_name = d.get('product_string', 'Attack Shark Mouse')
                if model_name == '2.4G Wireless Device':
                    model_name = "Attack Shark Mouse"
                return d['path'], mode, model_name
                
        return None, None, None

    def poll_loop(self):
        while self.running:
            path, mode, model_name = self.find_device_path()
            if not path:
                # No device found
                if self.status != "disconnected":
                    self.status = "disconnected"
                    self.update_tray()
                time.sleep(5)
                continue
                
            self.current_model = model_name
            if mode == "wired":
                # In wired mode, the mouse is charging/wired and does not report battery percentage packets
                if self.status != "charging":
                    self.status = "charging"
                    self.update_tray()
                time.sleep(5)
                continue
                
            # Mode is wireless
            try:
                dev = hid.device()
                dev.open_path(path)
                dev.set_nonblocking(True)
                
                if self.status in ("disconnected", "charging"):
                    # Do not display a made-up percentage while waiting for the first packet.
                    self.status = "waiting" if self.last_battery == -1 else "connected"
                    self.update_tray()
                
                last_recv_time = time.time()
                while self.running:
                    # Check if device changed mode (e.g. plugged in wire)
                    # We do a quick check every 5 seconds
                    if time.time() - last_recv_time > 5:
                        path_check, mode_check, model_check = self.find_device_path()
                        if not path_check or mode_check != "wireless":
                            break # Reconnect/reset loop
                        self.current_model = model_check
                        last_recv_time = time.time()
                        
                    try:
                        data = dev.read(64)
                        if data:
                            # Parse battery packet: starts with [0x03, 0x55, 0x40, 0x01]
                            if len(data) >= 5 and data[0] == 0x03 and data[1] == 0x55 and data[2] == 0x40 and data[3] == 0x01:
                                battery = data[4]
                                if 0 <= battery <= 100:
                                    self.last_battery = battery
                                    self.status = "connected"
                                    self.update_tray()
                                    last_recv_time = time.time()
                        time.sleep(0.1)
                    except IOError:
                        # Device disconnected or error
                        break
                        
                dev.close()
            except Exception as e:
                # Connection failed, retry later
                self.status = "disconnected"
                self.update_tray()
                time.sleep(5)

    def on_exit(self, icon, item):
        self.running = False
        self.icon.stop()

    def toggle_startup(self, icon, item):
        new_state = not item.checked
        set_startup(new_state)

    def open_project_page(self, icon, item):
        webbrowser.open(PROJECT_URL)

    def run(self):
        # Create system tray icon
        menu = pystray.Menu(
            pystray.MenuItem("Start with Windows", self.toggle_startup, checked=lambda item: is_startup_enabled()),
            pystray.MenuItem("Open source project", self.open_project_page),
            pystray.MenuItem("Exit", self.on_exit)
        )
        self.icon = pystray.Icon(
            "Attack Shark Battery",
            self.get_icon_data(),
            "Attack Shark X11: Initializing...",
            menu
        )
        
        # Start the polling loop in the background
        self.poll_thread.start()
        
        # Run the system tray icon event loop (blocks until stopped)
        self.icon.run()

def acquire_single_instance():
    global _mutex_handle
    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not _mutex_handle:
        return False
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
        return False
    return True


if __name__ == "__main__":
    if not acquire_single_instance():
        ctypes.windll.user32.MessageBoxW(
            None,
            "Attack Shark Battery Tray is already running in the notification area.",
            APP_NAME,
            0x40,
        )
        raise SystemExit(0)
    app = BatteryTrayApp()
    app.run()
