import time
import hid
from typing import Optional, Tuple, List
from .base import ProtocolHandler

RAZER_VID = 0x1532

RAZER_DEVICES = {
    0x00b3: "Razer HyperPolling Dongle",
    0x00b2: "Razer DeathAdder V3",
    0x00a5: "Razer Mouse",
}

def _razer_crc(buf: List[int]) -> int:
    """Calculate Razer XOR checksum over bytes 2 to 88."""
    crc = 0
    for b in buf[2:89]:
        crc ^= b
    return crc


def _razer_get_battery_query() -> List[int]:
    """Construct 90-byte Razer 'Get Battery Level' Feature Report query."""
    buf = [0] * 90
    buf[0] = 0x00  # Report ID
    buf[1] = 0x00  # Status (New Command)
    buf[2] = 0x1f  # Transaction ID
    buf[3] = 0x00  # Data Length High
    buf[4] = 0x03  # Data Length Low
    buf[5] = 0x07  # Class: Battery
    buf[6] = 0x02  # Command: Get Battery Level
    buf[89] = _razer_crc(buf)
    return buf


def _read_razer_battery(path: str) -> Tuple[Optional[int], Optional[bool]]:
    """Active: query Razer 90-byte feature report for battery % and charging status."""
    try:
        dev = hid.device()
        dev.open_path(path.encode('utf-8') if isinstance(path, str) else path)
        dev.set_nonblocking(True)
    except OSError:
        return None, None

    try:
        query = _razer_get_battery_query()
        try:
            dev.send_feature_report(bytes(query))
        except OSError:
            try:
                dev.write(bytes(query))
            except OSError:
                pass

        time.sleep(0.05)
        for _ in range(5):
            try:
                resp = dev.get_feature_report(0, 90)
            except OSError:
                try:
                    resp = dev.read(90)
                except OSError:
                    resp = None

            if resp and len(resp) >= 10:
                d = list(resp)
                # Verify response header (Class 0x07, Command 0x02)
                for idx in range(len(d) - 9):
                    if d[idx + 1] in (0x02, 0x00) and d[idx + 5] == 0x07 and d[idx + 6] == 0x02:
                        raw_batt = d[idx + 8]
                        charging_flag = d[idx + 9]
                        charging = bool(charging_flag in (1, 0x01))

                        if 0 <= raw_batt <= 100:
                            batt = raw_batt
                        elif 100 < raw_batt <= 255:
                            batt = int(round((raw_batt / 255.0) * 100))
                        else:
                            batt = None

                        if batt is not None:
                            return batt, charging
            time.sleep(0.03)
        return None, None
    finally:
        try:
            dev.close()
        except Exception:
            pass


class RazerProtocol(ProtocolHandler):
    def find_device(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        fallback = None
        for d in hid.enumerate(RAZER_VID):
            pid = d['product_id']
            name = RAZER_DEVICES.get(pid) or d.get('product_string') or "Razer Device"
            usage_page = d.get('usage_page', 0)
            usage = d.get('usage', 0)
            if usage_page == 0xff00 or (usage_page == 0x0001 and usage in (0x02, 0x06)):
                return (d['path'], "wireless", name)
            if fallback is None:
                fallback = (d['path'], "wireless", name)
        return fallback if fallback else (None, None, None)

    def handle_device(self, app, path: str, mode: str, model_name: str) -> None:
        app.current_model = model_name
        
        while app.running:
            batt, charging = _read_razer_battery(path)
            if batt is not None:
                if app.status in ("disconnected", "charging", "unknown"):
                    app.status = "connected"
                    app.update_tray()
                app.update_battery_level(batt, charging=bool(charging))
            else:
                break
                
            time.sleep(10)
