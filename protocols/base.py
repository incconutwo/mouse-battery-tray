import re
import time
import hid
from typing import Optional, Tuple, List, Dict, Set

class ProtocolHandler:
    def find_device(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Returns (path, mode, model_name) if top prioritized device is found, else (None, None, None)"""
        devices = self.find_all_devices()
        return devices[0] if devices else (None, None, None)

    def find_all_devices(self) -> List[Tuple[str, str, str]]:
        """Returns list of all connected device tuples: [(path, mode, model_name), ...]"""
        return []

    def handle_device(self, app, path: str, mode: str, model_name: str) -> None:
        """Take over polling for the device. Should return when device disconnects."""
        pass


def get_physical_device_key(d: dict) -> str:
    """
    Generate a unique identifier for a physical USB device instance.
    All HID interface collections belonging to the same physical mouse / dongle
    will produce the exact same physical device key.
    """
    vid = d.get('vendor_id', 0)
    pid = d.get('product_id', 0)
    
    # 1. Serial Number (if available and non-generic)
    serial = str(d.get('serial_number') or '').strip()
    if serial and serial.lower() not in ('0', '00000000', '1.00', '0000'):
        return f"{vid:04x}:{pid:04x}:{serial}"

    # 2. Extract parent device instance ID from Windows HID path
    path = d.get('path', '')
    if isinstance(path, bytes):
        path = path.decode('utf-8', errors='replace')
    path_str = str(path).lower()

    # Windows HID path structure:
    # \\?\hid#vid_1d57&pid_fa60&mi_02#7&1f2d3e4&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}
    # \\?\hid#vid_1d57&pid_fa60#7&1f2d3e4&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}
    parts = path_str.split('#')
    if len(parts) >= 3:
        parent_instance = parts[2]
        # Clean parent_instance if interface numbers are appended
        parent_instance = re.sub(r'&mi_[0-9a-f]+', '', parent_instance)
        return f"{vid:04x}:{pid:04x}:{parent_instance}"

    # Fallback: path string or vid:pid
    return f"{vid:04x}:{pid:04x}:{path_str}"


def find_hid_device_paths(supported_vids: Set[int], supported_devices: Dict) -> List[Tuple[str, str, str]]:
    """
    Scan HID devices and return ONE primary candidate tuple per physical mouse:
    [(primary_path, mode, model_name), ...], grouped by physical device key.
    """
    device_candidates: Dict[str, List[Tuple[int, str, str, str]]] = {}

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

            # Score endpoint suitability: higher score = higher priority
            if (if_num == 2 and usage_page == 10) or usage_page in (10, 0xff04):
                score = 40
            elif usage_page >= 0xff00 or if_num == 2:
                score = 30
            elif if_num in (1, 3):
                score = 20
            else:
                score = 10

            key = get_physical_device_key(d)
            if key not in device_candidates:
                device_candidates[key] = []
            device_candidates[key].append((score, d['path'], mode, model_name))

    result = []
    for key, candidates in device_candidates.items():
        # Sort by score descending and pick top endpoint as primary_path for this physical mouse
        candidates.sort(key=lambda x: x[0], reverse=True)
        top = candidates[0]
        result.append((top[1], top[2], top[3]))

    return result


def get_candidate_paths_for_device(primary_path: str, supported_vids: Set[int]) -> List[str]:
    """
    Get all HID endpoint candidate paths belonging to the SAME physical device as primary_path.
    Used by handle_device to open all endpoints of that specific mouse.
    """
    target_key = None
    all_devs = hid.enumerate()
    for d in all_devs:
        p = d['path']
        if p == primary_path or (isinstance(primary_path, bytes) and p == primary_path.decode('utf-8', errors='replace')):
            target_key = get_physical_device_key(d)
            break

    if not target_key:
        return [primary_path]

    matching_paths = []
    for d in all_devs:
        if d['vendor_id'] in supported_vids and get_physical_device_key(d) == target_key:
            matching_paths.append(d['path'])

    # Ensure primary_path is first
    if primary_path in matching_paths:
        matching_paths.remove(primary_path)
    matching_paths.insert(0, primary_path)
    return matching_paths
