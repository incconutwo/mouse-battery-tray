import os
import sys
import time
import hid

LOG_FILE = "mouse_hid_report_dump.txt"

TARGET_VIDS = {
    0x1d57, 0x25a7, 0x3710, 0x258a, 0x0c45, 0x093a, 0x24ae, 0x1bcf,
    0x3554, 0x320f, 0x3537, 0x3770, 0x373e, 0x33e4, 0x046a, 0x36a7, 0x1532
}

def log(msg, log_fp):
    print(msg)
    log_fp.write(msg + "\n")

def hex_dec_str(data):
    if not data:
        return "[]"
    dec_parts = [f"{b:3d}" for b in data]
    hex_parts = [f"{b:02X}" for b in data]
    return f"DEC: [{', '.join(dec_parts)}]\n   HEX: [{', '.join(hex_parts)}]"

def dump_mouse_reports():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        log("============================================================", f)
        log("      MOUSE HID RAW TELEMETRY REPORT DUMPER TOOL v1.0", f)
        log("============================================================", f)
        log(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n", f)

        all_devs = hid.enumerate()
        matching_devs = []

        for d in all_devs:
            vid = d['vendor_id']
            pid = d['product_id']
            prod = str(d.get('product_string', '') or '').lower()

            if vid in TARGET_VIDS or any(kw in prod for kw in ['mouse', 'dongle', 'receiver', 'vxe', 'pulsar', 'gwolves', 'g-wolves', 'attack shark', 'lamzu', 'scyrox']):
                matching_devs.append(d)

        if not matching_devs:
            log("No matching target gaming mice/receivers detected!", f)
            log("\nList of all detected HID devices on system:", f)
            for d in all_devs:
                log(f" - VID: 0x{d['vendor_id']:04x}, PID: 0x{d['product_id']:04x}, Name: {d.get('product_string')}", f)
            return

        log(f"Found {len(matching_devs)} candidate HID endpoints for testing.\n", f)

        # Group by VID/PID
        by_device = {}
        for d in matching_devs:
            key = (d['vendor_id'], d['product_id'], d.get('product_string', 'Gaming Mouse'))
            if key not in by_device:
                by_device[key] = []
            by_device[key].append(d)

        for (vid, pid, prod_name), endpoints in by_device.items():
            log("-" * 65, f)
            log(f"DEVICE: {prod_name} (VID: 0x{vid:04X}, PID: 0x{pid:04X})", f)
            log(f"Endpoints Count: {len(endpoints)}", f)
            log("-" * 65, f)

            for idx, ep in enumerate(endpoints, 1):
                path = ep['path']
                if_num = ep.get('interface_number', -1)
                up = ep.get('usage_page', 0)
                u = ep.get('usage', 0)

                log(f"\n --- Endpoint #{idx} ---", f)
                log(f" Path: {path}", f)
                log(f" Interface: {if_num}, Usage Page: 0x{up:04X}, Usage: 0x{u:04X}", f)

                try:
                    dev = hid.device()
                    dev.open_path(path.encode('utf-8') if isinstance(path, str) else path)
                    dev.set_nonblocking(True)
                except Exception as e:
                    log(f" [!] Could not open path: {e}", f)
                    continue

                try:
                    # 1. Passive Input Reads (3 seconds loop)
                    log(" Listening for passive HID input reports (3 seconds)...", f)
                    start = time.time()
                    read_count = 0
                    while time.time() - start < 3.0:
                        try:
                            data = dev.read(64)
                            if data:
                                read_count += 1
                                log(f" [PASSIVE READ #{read_count}] Report ID: 0x{data[0]:02X}, Len: {len(data)}", f)
                                log(f"   {hex_dec_str(list(data))}", f)
                        except Exception as e:
                            log(f"   Error reading: {e}", f)
                            break
                        time.sleep(0.05)

                    if read_count == 0:
                        log(" (No passive packets received on this endpoint)", f)

                    # 2. Query Packets (Feature Send & Get)
                    query_packets = [
                        [0x00, 0x06, 0x00, 0x00],
                        [0x06, 0x00, 0x00, 0x00],
                        [0x00, 0x03, 0x00, 0x00],
                        [0x00, 0x04, 0x00, 0x00],
                        [0x00, 0x83, 0x00, 0x00],
                        [0x03, 0x00, 0x00, 0x00],
                    ]

                    log(" Testing Feature Report Queries...", f)
                    for q_idx, q in enumerate(query_packets, 1):
                        try:
                            padded = q + [0x00] * (64 - len(q))
                            dev.send_feature_report(bytes(padded))
                            log(f" [SENT FEATURE QUERY #{q_idx}] 0x{q[0]:02X} 0x{q[1]:02X}", f)
                        except Exception as e:
                            pass

                        time.sleep(0.05)

                        for r_id in (0, 1, 2, 3, 4, 5, 6, 7, 0x83):
                            try:
                                resp = dev.get_feature_report(r_id, 64)
                                if resp:
                                    log(f"   [GET_FEATURE_REPORT Reply (r_id=0x{r_id:02X})]", f)
                                    log(f"   {hex_dec_str(list(resp))}", f)
                            except Exception:
                                pass

                finally:
                    try:
                        dev.close()
                    except Exception:
                        pass

        log("\n" + "=" * 65, f)
        log(" DUMP COMPLETED SUCCESSFULLY!", f)
        log(f" Log saved to: {os.path.abspath(LOG_FILE)}", f)
        log(" Please copy the log content or attach 'mouse_hid_report_dump.txt' when reporting!", f)
        log("=" * 65, f)

def main():
    dump_mouse_reports()
    print("\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main()
