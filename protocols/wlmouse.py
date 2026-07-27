import time
import hid
from typing import Optional, Tuple, List
from .base import ProtocolHandler, get_physical_device_key

WLMOUSE_VID = 0x36a7

WLMOUSE_DEVICES = {
    0xa887: "WLMouse Beast X",
    0xa868: "WLMouse Beast X Mini Pro",
}

WLMOUSE_QUERY = [0x00, 0x00, 0x02, 0x02, 0x00, 0x83]


def _wlmouse_parse(resp: List[int]) -> Tuple[Optional[int], Optional[bool]]:
    """Parse a data reply 'a1 00 02 02 00 83 <charge> <batt>' -> (batt, charging)."""
    if not resp:
        return None, None
    for i in range(5, len(resp) - 2):
        if (resp[i] == 0x83 and resp[i - 1] == 0x00 and resp[i - 2] == 0x02
                and resp[i - 5] in (0xa1, 0xa2)):
            charge = resp[i + 1]
            batt = resp[i + 2]
            if 0 <= batt <= 100:
                return batt, bool(charge)
    return None, None


def _wlmouse_read_feature(path: str) -> Tuple[Optional[int], Optional[bool]]:
    """Active: replay the HUB's 0x83 read, poll the feature report for the reply."""
    try:
        dev = hid.device()
        dev.open_path(path.encode('utf-8') if isinstance(path, str) else path)
    except OSError:
        return None, None
    try:
        report = [0x00] + WLMOUSE_QUERY + [0x00] * (64 - len(WLMOUSE_QUERY))
        try:
            dev.send_feature_report(report)
        except OSError:
            pass
        for _ in range(15):
            time.sleep(0.05)
            for length in (65, 64):
                try:
                    resp = dev.get_feature_report(0, length)
                except OSError:
                    resp = None
                if resp:
                    batt, charging = _wlmouse_parse(list(resp))
                    if batt is not None:
                        return batt, charging
        return None, None
    finally:
        try:
            dev.close()
        except Exception:
            pass


def _wlmouse_read_passive(path: str, seconds: float = 6.0) -> Tuple[Optional[int], Optional[bool]]:
    """Fallback: catch the '03 00 <batt> <charge>' heartbeat. No writes at all."""
    try:
        dev = hid.device()
        dev.open_path(path.encode('utf-8') if isinstance(path, str) else path)
        dev.set_nonblocking(True)
    except OSError:
        return None, None
    deadline = time.time() + seconds
    try:
        while time.time() < deadline:
            try:
                data = dev.read(64)
            except OSError:
                break
            if data:
                d = list(data)
                for off in (0, 1):
                    if len(d) >= off + 4 and d[off] == 0x03 and d[off + 1] == 0x00:
                        batt = d[off + 2]
                        if 0 <= batt <= 100:
                            return batt, bool(d[off + 3])
            time.sleep(0.02)
    finally:
        try:
            dev.close()
        except Exception:
            pass
    return None, None


class WLMouseProtocol(ProtocolHandler):
    def find_all_devices(self) -> List[Tuple[str, str, str]]:
        best: dict = {}  # key -> (path, mode, name)
        fallback = None
        for d in hid.enumerate(WLMOUSE_VID):
            pid = d['product_id']
            name = WLMOUSE_DEVICES.get(pid) or d.get('product_string') or "WLMouse Device"
            key = get_physical_device_key(d)
            if d.get('usage_page') == 0xffff and d.get('usage') == 0x00:
                if key not in best:
                    best[key] = (d['path'], "wireless", name)
            elif d.get('usage_page') == 0xffff and fallback is None:
                fallback = (d['path'], "wireless", name)
        return [(info[0], info[1], info[2]) for info in best.values()] if best else ([fallback] if fallback else [])

    def find_device(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        devices = self.find_all_devices()
        return devices[0] if devices else (None, None, None)

    def handle_device(self, app, path: str, mode: str, model_name: str) -> None:
        app.current_model = model_name
        
        # WLMouse polling is synchronous per iteration, we just return after a single poll
        # and the main poll_loop will re-discover and sleep.
        # But to be consistent with the other handlers, we can just take over the thread 
        # and do a polling loop here with a 10s delay.
        
        while app.running:
            batt, charging = _wlmouse_read_feature(path)
            if batt is None:
                for d in hid.enumerate(WLMOUSE_VID):
                    b, c = _wlmouse_read_passive(d['path'], seconds=4.0)
                    if b is not None:
                        batt, charging = b, c
                        break

            if batt is not None:
                app.update_device_state(path, model_name, batt, charging=bool(charging), activity=True)
            else:
                # Disconnected or failed to read
                # Break to allow main loop to rescan
                break
                
            time.sleep(10)
