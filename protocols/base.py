import time
import hid
from typing import Optional, Tuple, List, Dict, Set

class ProtocolHandler:
    def find_device(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Returns (path, mode, model_name) if device is found, else (None, None, None)"""
        return None, None, None

    def handle_device(self, app, path: str, mode: str, model_name: str) -> None:
        """Take over polling for the device. Should return when device disconnects."""
        pass

def find_hid_device_paths(supported_vids: Set[int], supported_devices: Dict) -> List[Tuple[str, str, str]]:
    """
    Scan HID devices and return ALL matching endpoint candidate tuples:
    [(path, mode, model_name), ...], prioritized by best vendor endpoint match.
    """
    p1_matches = []
    p2_matches = []
    p3_matches = []
    fallbacks = []

    for d in hid.enumerate():
        vid = d['vendor_id']
        pid = d['product_id']
        if vid in supported_vids:
            prod_string = str(d.get('product_string', '')).lower()
            if any(k in prod_string for k in ['keyboard', 'microphone', 'audio', 'headset', 'sound']):
                continue

            if_num = d.get('interface_number', -1)
            usage_page = d.get('usage_page', 0)

            if (vid, pid) in supported_devices:
                model_name, mode = supported_devices[(vid, pid)]
            elif pid in supported_devices:
                model_name, mode = supported_devices[pid]
            else:
                mode = "wired" if "wired" in prod_string else "wireless"
                model_name = d.get('product_string', 'Gaming Mouse')
                if model_name in ['2.4G Wireless Device', '2.4G Receiver']:
                    model_name = "Wireless Mouse"

            if "wired" in prod_string:
                mode = "wired"

            item = (d['path'], mode, model_name)

            if (if_num == 2 and usage_page == 10) or usage_page in (10, 0xff04):
                p1_matches.append(item)
            elif usage_page >= 0xff00 or if_num == 2:
                p2_matches.append(item)
            elif if_num in (1, 3):
                p3_matches.append(item)
            else:
                fallbacks.append(item)

    result = []
    seen = set()
    for item in (p1_matches + p2_matches + p3_matches + fallbacks):
        path = item[0]
        if path not in seen:
            seen.add(path)
            result.append(item)

    return result
