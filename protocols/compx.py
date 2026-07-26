import time
import hid
from typing import Optional, Tuple
from .base import ProtocolHandler, find_hid_device_paths
from .utils import parse_battery_telemetry

COMPX_VIDS = {0x25a7, 0x3710, 0x258a, 0x0c45, 0x093a, 0x24ae, 0x1bcf, 0x3554, 0x320f, 0x3537, 0x3770, 0x373e, 0x33e4, 0x046a}

COMPX_DEVICES = {
    # Pulsar Xlite / X2 Series
    (0x25a7, 0xfa7c): ("Pulsar X2 / Xlite Series", "wireless"),
    (0x25a7, 0xfa7b): ("Pulsar X2 / Xlite Series", "wired"),
    0xfa7c: ("Pulsar X2 / Xlite Series", "wireless"),
    0xfa7b: ("Pulsar X2 / Xlite Series", "wired"),

    # Pulsar 8K Dongle Gen.2 & CrazyLight Series
    (0x3710, 0x5406): ("Pulsar 8K Dongle Gen.2", "wireless"),
    (0x3710, 0x3414): ("Pulsar X2 CrazyLight", "wired"),
    (0x3710, 0x3510): ("Pulsar X2N CrazyLight", "wired"),
    0x5406: ("Pulsar 8K Dongle Gen.2", "wireless"),
    0x3414: ("Pulsar X2 CrazyLight", "wired"),
    0x3510: ("Pulsar X2N CrazyLight", "wired"),

    # VXE R1 Series
    (0x3554, 0xf58e): ("VXE R1 Series", "wireless"),
    (0x3554, 0xf58a): ("VXE R1 Pro / Pro Max", "wireless"),
    (0x320f, 0x5055): ("VXE R1 Series", "wireless"),
    0xf58e: ("VXE R1 Series", "wireless"),
    0xf58a: ("VXE R1 Pro / Pro Max", "wireless"),
    0x5055: ("VXE R1 Series", "wireless"),

    # Scyrox V6
    (0x3554, 0xf5f7): ("Scyrox V6 8K", "wireless"),
    0xf5f7: ("Scyrox V6 8K", "wireless"),

    # Lamzu Maya X
    (0x373e, 0x001e): ("Lamzu Maya X 8K", "wireless"),
    0x001e: ("Lamzu Maya X 8K", "wireless"),

    # G-Wolves Series
    (0x33e4, 0x3854): ("G-Wolves Fenrir Pro 8K", "wireless"),
    (0x33e4, 0x3619): ("G-Wolves Fenrir Pro 8K", "wired"),
    (0x33e4, 0x5617): ("G-Wolves HTX Ultra 8K", "wireless"),
    (0x33e4, 0x5608): ("G-Wolves HTX Ultra 8K", "wired"),
    0x3854: ("G-Wolves Fenrir Pro 8K", "wireless"),
    0x3619: ("G-Wolves Fenrir Pro 8K", "wired"),
    0x5617: ("G-Wolves HTX Ultra 8K", "wireless"),
    0x5608: ("G-Wolves HTX Ultra 8K", "wired"),

    # MAMBASNAKE M5 Ultra
    (0x373e, 0x0050): ("Mambasnake M5 Ultra", "wireless"),
    (0x373e, 0x0051): ("Mambasnake M5 Ultra", "wired"),
    0x0050: ("Mambasnake M5 Ultra", "wireless"),
    0x0051: ("Mambasnake M5 Ultra", "wired"),

    # Hitscan Hyperlight
    (0x3770, 0x0300): ("Hitscan Hyperlight", "wireless"),
    (0x3770, 0x0200): ("Hitscan Hyperlight", "wireless"),
    0x0300: ("Hitscan Hyperlight", "wireless"),
    0x0200: ("Hitscan Hyperlight", "wireless"),

    # Cherry Xtrfy M68 Wireless
    (0x046a, 0x0330): ("Cherry Xtrfy M68 Wireless", "wireless"),
    (0x046a, 0x0334): ("Cherry Xtrfy M68 Wireless", "wired"),
    0x0330: ("Cherry Xtrfy M68 Wireless", "wireless"),
    0x0334: ("Cherry Xtrfy M68 Wireless", "wired"),

    # Incott G24 Pro
    (0x093a, 0x522c): ("Incott G24 Pro", "wireless"),
    (0x093a, 0x622c): ("Incott G24 Pro", "wired"),
    0x522c: ("Incott G24 Pro", "wireless"),
    0x622c: ("Incott G24 Pro", "wired"),
}

class CompxProtocol(ProtocolHandler):
    def find_device(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        paths = find_hid_device_paths(COMPX_VIDS, COMPX_DEVICES)
        return paths[0] if paths else (None, None, None)

    def handle_device(self, app, primary_path: str, mode: str, model_name: str) -> None:
        app.current_model = model_name
        if mode == "wired":
            if app.status != "charging":
                app.status = "charging"
                app.update_tray()
            time.sleep(5)
            return

        candidate_tuples = find_hid_device_paths(COMPX_VIDS, COMPX_DEVICES)
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
            app.status = "disconnected"
            app.update_tray()
            time.sleep(5)
            return

        QUERY_PACKETS = [
            [0x00, 0x06, 0x00, 0x00],
            [0x06, 0x00, 0x00, 0x00],
            [0x00, 0x03, 0x00, 0x00],
            [0x00, 0x04, 0x00, 0x00],
            [0x00, 0x83, 0x00, 0x00],
            [0x03, 0x00, 0x00, 0x00],
        ]

        try:
            if app.status in ("disconnected", "charging", "unknown"):
                app.status = "connected"
                app.update_tray()

            last_recv_time = time.time()
            last_query_time = time.time() - 2.0

            while app.running:
                now = time.time()
                
                if now - last_recv_time > 5:
                    paths = find_hid_device_paths(COMPX_VIDS, COMPX_DEVICES)
                    path_check = paths[0][0] if paths else None
                    if not path_check or path_check not in candidate_paths:
                        break
                    last_recv_time = now

                got_packet = False
                for p, dev in open_devices:
                    try:
                        data = dev.read(64)
                        if data:
                            d_list = list(data)
                            dev_id = d_list[1] if len(d_list) > 1 else None
                            battery, is_charging = parse_battery_telemetry(d_list, dev_id, is_beken=False)
                            if battery is not None:
                                app.update_battery_level(battery, charging=is_charging)
                                last_recv_time = now
                                got_packet = True
                                break
                    except OSError:
                        pass

                if not got_packet and (app.last_battery < 0 or now - last_recv_time > 3.0) and (now - last_query_time >= 3.0):
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

                            for r_id in (0, 6, 3, 4):
                                try:
                                    resp = dev.get_feature_report(r_id, 64)
                                    if resp:
                                        d_list = list(resp)
                                        dev_id = d_list[1] if len(d_list) > 1 else None
                                        battery, is_charging = parse_battery_telemetry(d_list, dev_id, is_beken=False)
                                        if battery is not None:
                                            app.update_battery_level(battery, charging=is_charging)
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
