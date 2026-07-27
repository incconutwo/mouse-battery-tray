import time
import hid
from typing import Optional, Tuple, List
from .base import ProtocolHandler, get_physical_device_key

RAZER_VID = 0x1532

RAZER_DEVICES = {
    0x00b3: "Razer HyperPolling Dongle",
    0x00b2: "Razer DeathAdder V3",
    0x00a5: "Razer Mouse",
    0x00b6: "Razer DeathAdder V3 Pro",
    0x00aa: "Razer Viper V2 Pro",
    0x00ab: "Razer Viper V3 Pro",
    0x00a3: "Razer Basilisk V3 Pro",
    0x009a: "Razer Naga V2 Pro",
    0x0088: "Razer Mamba",
}

# Razer 90-byte HID feature report layout (confirmed via OpenRazer/community reverse-engineering):
# buf[0]  = 0x00  Status byte (set to 0 on request; device writes response status here)
# buf[1]  = TX ID Transaction ID (use 0x1f for wireless battery queries)
# buf[2]  = 0x00  Remaining packets
# buf[3]  = 0x00  Protocol type
# buf[4]  = 0x00  (reserved)
# buf[5]  = 0x02  Data size (number of meaningful args)
# buf[6]  = 0x07  Command class  (0x07 = Battery)
# buf[7]  = 0x02  Command ID     (0x02 = Get Battery Level)
# buf[8..87] = argument payload (zeros for a GET)
# buf[88] = CRC  (XOR of buf[2..87])
# buf[89] = 0x00 (reserved)
#
# Response: same 90-byte layout.
#   buf[8]  = raw battery 0-255 (where 255 == 100%)
#   buf[9]  = charging flag (1 = charging)


def _razer_crc(buf: List[int]) -> int:
    """XOR checksum over bytes 2..87 inclusive (per OpenRazer spec)."""
    crc = 0
    for b in buf[2:88]:
        crc ^= b
    return crc


def _razer_get_battery_query(transaction_id: int = 0x1f) -> bytes:
    """Construct the correct 90-byte Razer 'Get Battery Level' feature report."""
    buf = [0] * 90
    buf[0] = 0x00              # Status: new command
    buf[1] = transaction_id   # Transaction ID
    buf[2] = 0x00              # Remaining packets
    buf[3] = 0x00              # Protocol type
    buf[4] = 0x00              # Reserved
    buf[5] = 0x02              # Data size
    buf[6] = 0x07              # Command class: Battery
    buf[7] = 0x02              # Command ID: Get Battery Level
    buf[88] = _razer_crc(buf)  # CRC at index 88
    buf[89] = 0x00             # Reserved
    return bytes(buf)


def _parse_battery_response(resp: bytes, transaction_id: int) -> Tuple[Optional[int], Optional[bool]]:
    """
    Parse a Razer 90-byte response for battery data.
    Looks for the response marker (status=0x02 meaning 'success') with matching
    command class 0x07 and command ID 0x02 at the standard offsets.
    Returns (battery_percent, is_charging) or (None, None) if no valid data found.
    """
    if not resp or len(resp) < 10:
        return None, None

    d = list(resp)
    # Standard layout: response status at [0], tx_id at [1], class at [6], cmd at [7],
    # data at [8] (battery raw) and [9] (charging flag)
    # Status 0x02 = command successful; also accept 0x01 (busy but data may be present)
    if d[0] in (0x02, 0x01) and d[6] == 0x07 and d[7] == 0x02:
        raw_batt = d[8]
        charging_flag = d[9]
        charging = bool(charging_flag == 0x01)
        if raw_batt == 0:
            return None, None
        # Razer reports battery as 0-255 range (255 = 100%)
        batt = int(round((raw_batt / 255.0) * 100)) if raw_batt > 100 else raw_batt
        if 1 <= batt <= 100:
            return batt, charging

    # Fallback: scan the buffer in case the device offsets the response
    for base in range(min(len(d) - 9, 4)):
        if d[base] in (0x02, 0x01) and d[base + 6] == 0x07 and d[base + 7] == 0x02:
            raw_batt = d[base + 8]
            if raw_batt == 0:
                continue
            charging = bool(d[base + 9] == 0x01)
            batt = int(round((raw_batt / 255.0) * 100)) if raw_batt > 100 else raw_batt
            if 1 <= batt <= 100:
                return batt, charging

    return None, None


def _read_razer_battery(path: str) -> Tuple[Optional[int], Optional[bool]]:
    """
    Query Razer device at 'path' using the correct 90-byte HID feature report protocol.
    Tries multiple transaction IDs (0x1f, 0x3f) and both feature-report and interrupt-read
    fallbacks for maximum compatibility across device generations.
    """
    raw_path = path.encode('utf-8') if isinstance(path, str) else path
    try:
        dev = hid.device()
        dev.open_path(raw_path)
        dev.set_nonblocking(True)
    except OSError:
        return None, None

    try:
        for tx_id in (0x1f, 0x3f, 0xff):
            query = _razer_get_battery_query(tx_id)
            sent = False
            try:
                dev.send_feature_report(query)
                sent = True
            except OSError:
                pass

            if not sent:
                try:
                    dev.write(query)
                    sent = True
                except OSError:
                    pass

            if not sent:
                continue

            time.sleep(0.06)
            for _ in range(4):
                resp = None
                try:
                    resp = bytes(dev.get_feature_report(0x00, 91))
                    if resp and len(resp) == 91:
                        resp = resp[1:]  # strip leading report-ID byte hidapi sometimes prepends
                except OSError:
                    pass

                if not resp or len(resp) < 10:
                    try:
                        resp = bytes(dev.read(90))
                    except OSError:
                        pass

                batt, charging = _parse_battery_response(resp, tx_id)
                if batt is not None:
                    return batt, charging

                time.sleep(0.03)

        return None, None
    finally:
        try:
            dev.close()
        except Exception:
            pass


def _score_razer_interface(d: dict) -> int:
    """
    Score a HID interface for suitability as a Razer battery query target.
    Higher score = more likely to accept feature reports without being locked
    by the Windows HID driver for exclusive access.
    
    Razer devices expose several interfaces:
    - usage_page=0x0001, usage=0x0002 → Generic Mouse (input only, usually locked)
    - usage_page=0x0001, usage=0x0006 → Generic Keyboard/Control (can accept feature reports)
    - usage_page=0xff00 → Vendor-specific (often exclusive-access locked on Windows by Synapse)
    - interface_number=3 → Typically the "control" interface used by Synapse for configs
    """
    usage_page = d.get('usage_page', 0)
    usage = d.get('usage', 0)
    iface = d.get('interface_number', -1)
    score = 0

    if usage_page == 0x0001 and usage == 0x0006:  # best: keyboard-type control iface
        score = 30
    elif iface == 3:  # known Synapse control interface number
        score = 25
    elif usage_page == 0x0001 and usage == 0x0002:  # mouse input – often locked
        score = 10
    elif usage_page == 0xff00:  # vendor – may be locked by Synapse on Windows
        score = 5
    elif iface >= 0:
        score = 1  # any other interface as absolute last resort

    return score


class RazerProtocol(ProtocolHandler):
    def find_all_devices(self) -> List[Tuple[str, str, str]]:
        """
        Enumerate all Razer HID interfaces and pick the best one per PID.
        Avoids exclusive-access interfaces that block feature-report writes on Windows.
        """
        # Group by physical_device_key, track best-scored interface per physical device
        best: dict = {}  # key -> (score, path, name)

        for d in hid.enumerate(RAZER_VID):
            pid = d['product_id']
            name = RAZER_DEVICES.get(pid) or d.get('product_string') or "Razer Device"
            score = _score_razer_interface(d)
            if score == 0:
                continue
            key = get_physical_device_key(d)
            if key not in best or score > best[key][0]:
                best[key] = (score, d['path'], name)

        return [(info[1], "wireless", info[2]) for info in best.values()]

    def find_device(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        devices = self.find_all_devices()
        return devices[0] if devices else (None, None, None)

    def handle_device(self, app, path: str, mode: str, model_name: str) -> None:
        app.current_model = model_name

        while app.running:
            batt, charging = _read_razer_battery(path)
            if batt is not None:
                app.update_device_state(path, model_name, batt, charging=bool(charging), activity=True)
            else:
                break

            time.sleep(10)
