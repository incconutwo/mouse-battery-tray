import sys
import time
import threading
import urllib.request
import json
import webbrowser
import ctypes
from typing import Optional, Tuple, List

import hid
import pystray

from config import (
    trim_memory,
    acquire_single_instance,
    is_startup_enabled,
    set_startup,
    get_alert_threshold,
    set_alert_threshold,
    get_show_estimate,
    set_show_estimate,
    is_light_mode,
    get_battery_history,
    set_battery_history,
)
from updater import (
    __version__,
    GITHUB_REPO_URL,
    GITHUB_RELEASES_API,
    GITHUB_RELEASES_URL,
    is_newer_version,
)
from devices import (
    find_device_path,
    find_device_paths,
    parse_battery_telemetry,
    find_wlmouse,
    read_wlmouse_battery,
    find_razer,
    read_razer_battery,
    BEKEN_DEVICE_NAMES,
)
from icon_drawer import get_icon_data


# =============================================================================
# Tray Application
# =============================================================================
class BatteryTrayApp:
    def __init__(self):
        self.icon = None
        self.running = True
        self.last_battery = -1
        self.status = "disconnected"
        self.charging = False
        self.current_model = "Mouse"
        
        # Alert threshold & state (saved in registry)
        self.alert_threshold: int = get_alert_threshold()
        self.has_alerted: bool = False
        
        # Hours Estimate state (saved in registry)
        self.show_estimate: bool = get_show_estimate()
        saved_history, saved_anchored = get_battery_history()
        self.battery_history: List[Tuple[float, int]] = saved_history
        self.is_anchored: bool = saved_anchored
        
        # Update checker state
        self.latest_version: Optional[str] = None
        self.update_url: str = GITHUB_RELEASES_URL
        self.update_status: str = "idle"  # idle | checking | available | up_to_date | error
        self.last_update_check_time: float = time.time()
        
        # Icon caching, theme & polling state
        self.last_theme: bool = is_light_mode()
        self._icon_cache = {}
        self.poll_thread = threading.Thread(target=self.poll_loop, daemon=True)

    def check_for_updates(self, manual: bool = False):
        """Asynchronously fetch the latest release tag from GitHub."""
        self.update_status = "checking"
        if self.icon:
            self.icon.menu = self.create_menu()

        def _worker():
            try:
                req = urllib.request.Request(
                    GITHUB_RELEASES_API,
                    headers={"User-Agent": "MouseBatteryTray-UpdateChecker"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        tag_name = data.get("tag_name", "")
                        html_url = data.get("html_url", GITHUB_RELEASES_URL)
                        self.update_url = html_url
                        if tag_name and is_newer_version(tag_name, __version__):
                            self.latest_version = tag_name
                            self.update_status = "available"
                        else:
                            self.update_status = "up_to_date"
                    else:
                        self.update_status = "error"
            except urllib.error.HTTPError as e:
                # 404 means no release exists yet on GitHub
                if e.code == 404:
                    self.update_status = "up_to_date"
                else:
                    self.update_status = "error"
            except Exception:
                self.update_status = "error"

            if self.icon:
                self.icon.menu = self.create_menu()
                if manual:
                    if self.update_status == "up_to_date":
                        try:
                            self.icon.notify(f"You are on the latest version ({__version__}).", "Mouse Battery Tray")
                        except Exception:
                            pass
                    elif self.update_status == "error":
                        try:
                            self.icon.notify("Could not check for updates. Please try again later.", "Mouse Battery Tray")
                        except Exception:
                            pass
                if self.update_status == "available":
                    try:
                        self.icon.notify(f"New update {self.latest_version} available! Click menu to download.", "Mouse Battery Tray")
                    except Exception:
                        pass
            trim_memory()

        threading.Thread(target=_worker, daemon=True).start()

    def open_update_url(self, icon, item):
        webbrowser.open(self.update_url)

    def open_repo_url(self, icon, item):
        webbrowser.open(GITHUB_REPO_URL)

    def open_kofi_url(self, icon, item):
        webbrowser.open("https://ko-fi.com/incconutwo")

    def on_check_updates_click(self, icon, item):
        self.check_for_updates(manual=True)

    def toggle_show_estimate(self, icon, item):
        self.show_estimate = not self.show_estimate
        set_show_estimate(self.show_estimate)
        self.update_tray()
        if self.icon:
            self.icon.menu = self.create_menu()

    def set_threshold(self, threshold: int):
        self.alert_threshold = threshold
        set_alert_threshold(threshold)
        if self.alert_threshold == 0 or self.last_battery > self.alert_threshold:
            self.has_alerted = False
        if self.icon:
            self.icon.menu = self.create_menu()

    def get_battery_estimate_str(self) -> Optional[str]:
        if not self.show_estimate or self.charging or self.last_battery <= 0:
            return None
            
        if len(self.battery_history) < 2:
            return None
            
        now = time.time()
        recent_history = [(t, b) for t, b in self.battery_history if now - t <= 14400]
        if len(recent_history) < 2:
            return None
            
        t_first, b_first = recent_history[0]
        t_last, b_last = recent_history[-1]
        
        time_span = t_last - t_first
        pct_drop = b_first - b_last
        
        if time_span < 30 or pct_drop <= 0:
            return None
            
        drain_rate = pct_drop / time_span
        if drain_rate <= 0:
            return None
            
        remaining_seconds = self.last_battery / drain_rate
        hours = int(remaining_seconds // 3600)
        minutes = int((remaining_seconds % 3600) // 60)
        
        if hours > 300:
            return None
            
        if hours >= 1:
            return f"~{hours}h {minutes}m" if minutes > 0 else f"~{hours}h"
        elif minutes > 0:
            return f"~{minutes}m"
        else:
            return "~<1m"

    def update_battery_level(self, battery: int, charging: bool = False):
        self.last_battery = battery
        self.charging = charging
        self.status = "charging" if charging else "connected"
        
        now = time.time()
        time_since_last_poll = now - getattr(self, '_last_update_call', now)
        self._last_update_call = now
        pc_slept = (time_since_last_poll > 1800)

        if charging:
            self.battery_history.clear()
            self.is_anchored = False
            set_battery_history([], False)
        elif battery >= 0:
            if not self.battery_history:
                self.battery_history = [(now, battery)]
                self.is_anchored = False
                set_battery_history(self.battery_history, False)
            else:
                last_time, last_pct = self.battery_history[-1]
                
                if pc_slept and battery != last_pct:
                    # Battery changed while PC was asleep; drop time is unknown.
                    self.battery_history = [(now, battery)]
                    self.is_anchored = False
                    set_battery_history(self.battery_history, False)
                elif battery < last_pct:
                    # Battery level dropped!
                    if not self.is_anchored:
                        # First drop: anchor the initial timestamp if we monitored it continuously.
                        # This gives an estimate on the first drop.
                        self.battery_history.append((now, battery))
                        self.is_anchored = True
                    else:
                        # Subsequent drop. Append to history.
                        self.battery_history.append((now, battery))
                        
                    # Prune stale entries (>4h) BEFORE saving to registry
                    self.battery_history = [(t, b) for t, b in self.battery_history if now - t <= 14400]
                    set_battery_history(self.battery_history, True)
                elif battery > last_pct + 5:
                    # Battery increased significantly without charging flag: reset history.
                    self.battery_history = [(now, battery)]
                    self.is_anchored = False
                    set_battery_history(self.battery_history, False)

        self.update_tray()

        # Trigger Low Battery Toast Notification if below threshold
        threshold = self.alert_threshold
        if threshold > 0 and not charging:
            if battery <= threshold and not self.has_alerted:
                self.has_alerted = True
                if self.icon:
                    try:
                        model = self.current_model or "Mouse"
                        self.icon.notify(
                            f"{model} battery level is low ({battery}%). Please connect charger.",
                            "Low Battery Alert"
                        )
                    except Exception:
                        pass
            elif battery > threshold + 5:
                self.has_alerted = False
        elif charging:
            self.has_alerted = False

    def create_menu(self) -> pystray.Menu:
        items = []
        if self.update_status == "available" and self.latest_version:
            items.append(pystray.MenuItem(f"🚀 Update Available ({self.latest_version})", self.open_update_url))
            items.append(pystray.Menu.SEPARATOR)
        
        def _make_threshold_item(val: int, label: str):
            return pystray.MenuItem(
                label,
                lambda icon, item: self.set_threshold(val),
                checked=lambda item: self.alert_threshold == val,
                radio=True
            )

        threshold_menu = pystray.Menu(
            _make_threshold_item(25, "25%"),
            _make_threshold_item(20, "20% (Default)"),
            _make_threshold_item(15, "15%"),
            _make_threshold_item(10, "10%"),
            pystray.Menu.SEPARATOR,
            _make_threshold_item(0, "Disabled")
        )

        items.append(pystray.MenuItem("Start with Windows", self.toggle_startup, checked=lambda item: is_startup_enabled()))
        items.append(pystray.MenuItem("Show Hours Estimate", self.toggle_show_estimate, checked=lambda item: self.show_estimate))
        items.append(pystray.MenuItem("Low Battery Alert", threshold_menu))

        if self.update_status == "checking":
            items.append(pystray.MenuItem("🔄 Checking for updates...", None, enabled=False))
        else:
            items.append(pystray.MenuItem("Check for Updates", self.on_check_updates_click))
            
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(f"Mouse Battery Tray {__version__}", self.open_repo_url))
        items.append(pystray.MenuItem("Donate / Support", self.open_kofi_url))
        items.append(pystray.MenuItem("Exit", self.on_exit))
        return pystray.Menu(*items)

    def update_tray(self):
        if not self.icon:
            return
        
        self.last_theme = is_light_mode()
        self.icon.icon = get_icon_data(self.status, self.last_battery, self._icon_cache)
        
        model = self.current_model or "Mouse"
        if self.status == "disconnected":
            self.icon.title = f"{model}: Disconnected"
        elif self.status == "connected" and self.last_battery < 0:
            self.icon.title = f"{model}: Waiting for battery reading..."
        elif self.status == "charging" and self.last_battery < 0:
            self.icon.title = f"{model}: Charging/Wired"
        elif self.status == "charging":
            self.icon.title = f"{model}: {self.last_battery}% (charging)"
        elif self.status == "unknown":
            self.icon.title = f"{model}: detected (battery unavailable)"
        else:
            est_str = self.get_battery_estimate_str()
            if est_str:
                self.icon.title = f"{model}: {self.last_battery}% ({est_str})"
            else:
                self.icon.title = f"{model}: {self.last_battery}%"

    def poll_loop(self):
        last_trim = time.time()
        while self.running:
            if time.time() - last_trim > 60:
                trim_memory()
                last_trim = time.time()

            if is_light_mode() != self.last_theme:
                self.update_tray()

            if time.time() - self.last_update_check_time >= 86400:
                self.last_update_check_time = time.time()
                self.check_for_updates(manual=False)

            path, mode, model_name = find_device_path()
            if path:
                self._handle_standard_device(path, mode, model_name)
                continue
                
            wl_path, wl_name, wl_pid = find_wlmouse()
            if wl_path:
                self.current_model = wl_name
                battery, charging = read_wlmouse_battery(wl_path)
                if battery is not None:
                    self.update_battery_level(battery, bool(charging))
                else:
                    self.status = "unknown"
                    self.update_tray()
                time.sleep(10)
                continue

            razer_path, razer_name, razer_pid = find_razer()
            if razer_path:
                self.current_model = razer_name
                battery, charging = read_razer_battery(razer_path)
                if battery is not None:
                    self.update_battery_level(battery, bool(charging))
                else:
                    self.status = "unknown"
                    self.update_tray()
                time.sleep(10)
                continue
                
            if self.status != "disconnected":
                self.status = "disconnected"
                self.update_tray()
            time.sleep(5)

    def _handle_standard_device(self, primary_path: str, mode: str, model_name: str):
        self.current_model = model_name
        if mode == "wired":
            if self.status != "charging":
                self.status = "charging"
                self.update_tray()
            time.sleep(5)
            return

        # Discover all candidate endpoint paths for this mouse
        candidate_tuples = find_device_paths()
        candidate_paths = [t[0] for t in candidate_tuples]
        if primary_path not in candidate_paths:
            candidate_paths.insert(0, primary_path)

        open_devices = []
        for p in candidate_paths:
            try:
                dev = hid.device()
                dev.open_path(p.encode('utf-8') if isinstance(p, str) else p)
                dev.set_nonblocking(True)
                open_devices.append((p, dev))
            except OSError:
                pass

        if not open_devices:
            self.status = "disconnected"
            self.update_tray()
            time.sleep(5)
            return

        try:
            if self.status in ("disconnected", "charging", "unknown"):
                self.status = "connected"
                self.update_tray()

            last_recv_time = time.time()
            last_trim_time = time.time()
            last_query_time = time.time() - 2.0  # Allow initial query after 1 second if passive reads fail

            # Active feature query packets to send if passive reads remain silent
            QUERY_PACKETS = [
                [0x00, 0x06, 0x00, 0x00],
                [0x06, 0x00, 0x00, 0x00],
                [0x00, 0x03, 0x00, 0x00],
                [0x00, 0x04, 0x00, 0x00],
                [0x00, 0x83, 0x00, 0x00],
                [0x03, 0x00, 0x00, 0x00],
            ]

            while self.running:
                now = time.time()
                if now - last_trim_time > 60:
                    trim_memory()
                    last_trim_time = now

                if is_light_mode() != self.last_theme:
                    self.update_tray()

                if now - self.last_update_check_time >= 86400:
                    self.last_update_check_time = now
                    self.check_for_updates(manual=False)

                if now - last_recv_time > 5:
                    path_check, mode_check, model_check = find_device_path()
                    if not path_check or mode_check != "wireless" or path_check not in candidate_paths:
                        break
                    self.current_model = model_check
                    last_recv_time = now

                got_packet = False
                for p, dev in open_devices:
                    try:
                        data = dev.read(64)
                        if data:
                            d_list = list(data)
                            dev_id = d_list[1] if len(d_list) > 1 else None
                            if dev_id in BEKEN_DEVICE_NAMES:
                                self.current_model = BEKEN_DEVICE_NAMES[dev_id]

                            battery, is_charging = parse_battery_telemetry(d_list, dev_id)
                            if battery is not None:
                                self.update_battery_level(battery, charging=is_charging)
                                last_recv_time = now
                                got_packet = True
                                break
                    except OSError:
                        pass

                # If no valid battery telemetry has been received for > 3s, attempt feature query reports
                if not got_packet and (self.last_battery < 0 or now - last_recv_time > 3.0) and (now - last_query_time >= 3.0):
                    last_query_time = now
                    for p, dev in open_devices:
                        if got_packet:
                            break
                        for q in QUERY_PACKETS:
                            try:
                                padded = q + [0x00] * (64 - len(q))
                                dev.send_feature_report(bytes(padded))
                            except Exception:
                                pass

                            # Poll get_feature_report for CompX / VXE NordicMouse feature-only endpoints
                            for r_id in (0, 6, 3, 4):
                                try:
                                    resp = dev.get_feature_report(r_id, 64)
                                    if resp:
                                        d_list = list(resp)
                                        dev_id = d_list[1] if len(d_list) > 1 else None
                                        battery, is_charging = parse_battery_telemetry(d_list, dev_id)
                                        if battery is not None:
                                            self.update_battery_level(battery, charging=is_charging)
                                            last_recv_time = now
                                            got_packet = True
                                            break
                                except Exception:
                                    pass
                            if got_packet:
                                break

                time.sleep(0.1)

        finally:
            for p, dev in open_devices:
                try:
                    dev.close()
                except Exception:
                    pass

    def on_exit(self, icon, item):
        self.running = False
        self.icon.stop()

    def toggle_startup(self, icon, item):
        new_state = not item.checked
        set_startup(new_state)

    def run(self):
        self.icon = pystray.Icon(
            "Mouse Battery Tray",
            get_icon_data(self.status, self.last_battery, self._icon_cache),
            "Mouse Battery Tray: Initializing...",
            self.create_menu()
        )
        
        self.poll_thread.start()
        self.check_for_updates(manual=False)
        self.icon.run()


if __name__ == "__main__":
    if not acquire_single_instance():
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                "Mouse Battery Tray is already running in the notification area.",
                "Mouse Battery Tray",
                0x40,  # MB_ICONINFORMATION
            )
        except Exception:
            pass
        sys.exit(0)
    app = BatteryTrayApp()
    app.run()
