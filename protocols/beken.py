import time
import hid
from typing import Optional, Tuple, List
from .base import ProtocolHandler, find_hid_device_paths, get_candidate_paths_for_device
from .utils import parse_battery_telemetry

BEKEN_VIDS = {0x1d57}

BEKEN_DEVICE_NAMES = {
    0x55: "Attack Shark X11",
    0x10: "Attack Shark R1",
    0x85: "Attack Shark X6",
    0x4d: "Attack Shark X3",
    0xbe: "Attack Shark X11 Pro",
    0x07: "Attack Shark X11 SE",
}

BEKEN_DEVICES = {
    (0x1d57, 0xfa60): ("Attack Shark Mouse", "wireless"),
    (0x1d57, 0xfa55): ("Attack Shark X11", "wired"),
    (0x1d57, 0xfa65): ("Attack Shark 8K Receiver", "wireless"),
    0xfa60: ("Attack Shark Mouse", "wireless"),
    0xfa55: ("Attack Shark X11", "wired"),
    0xfa65: ("Attack Shark 8K Receiver", "wireless"),
    
    (0x1d57, 0xfa61): ("Attack Shark R1", "wired"),
    0xfa61: ("Attack Shark R1", "wired"),
    
    (0x1d57, 0xfa50): ("Attack Shark X3", "wired"),
    0xfa50: ("Attack Shark X3", "wired"),
    
    (0x1d57, 0xfa62): ("Attack Shark X6", "wireless"),
    (0x1d57, 0xfa56): ("Attack Shark X6", "wired"),
    0xfa62: ("Attack Shark X6", "wireless"),
    0xfa56: ("Attack Shark X6", "wired"),
}

class BekenProtocol(ProtocolHandler):
    def find_all_devices(self) -> List[Tuple[str, str, str]]:
        return find_hid_device_paths(BEKEN_VIDS, BEKEN_DEVICES)

    def find_device(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        paths = self.find_all_devices()
        return paths[0] if paths else (None, None, None)

    def handle_device(self, app, primary_path: str, mode: str, model_name: str) -> None:
        app.current_model = model_name
        if mode == "wired":
            if app.status != "charging":
                app.status = "charging"
                app.update_tray()
            time.sleep(5)
            return

        candidate_paths = get_candidate_paths_for_device(primary_path, BEKEN_VIDS)

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
            app.status = "disconnected"
            app.update_tray()
            time.sleep(5)
            return

        try:
            if app.status in ("disconnected", "charging", "unknown"):
                app.status = "connected"
                app.update_tray()

            last_recv_time = time.time()

            while app.running:
                now = time.time()
                
                # Check for device disconnect / list update every 5 seconds
                if now - last_recv_time > 5:
                    current_devices = find_hid_device_paths(BEKEN_VIDS, BEKEN_DEVICES)
                    current_paths = [t[0] for t in current_devices]
                    if primary_path not in current_paths:
                        break
                    last_recv_time = now

                got_packet = False
                for p, dev in open_devices:
                    try:
                        data = dev.read(64)
                        if data:
                            d_list = list(data)
                            dev_id = d_list[1] if len(d_list) > 1 else None
                            if dev_id in BEKEN_DEVICE_NAMES:
                                app.current_model = BEKEN_DEVICE_NAMES[dev_id]

                            battery, is_charging = parse_battery_telemetry(d_list, dev_id, is_beken=True)
                            if battery is not None:
                                app.update_device_state(primary_path, app.current_model, battery, charging=is_charging, activity=True)
                                last_recv_time = now
                                got_packet = True
                                break
                    except OSError:
                        pass
                
                if got_packet:
                    pass  # Processed battery
                    
                time.sleep(0.1)

        finally:
            for p, dev in open_devices:
                try:
                    dev.close()
                except Exception:
                    pass
