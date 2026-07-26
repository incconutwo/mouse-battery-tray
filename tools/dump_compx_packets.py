#!/usr/bin/env python3
"""
dump_compx_packets.py — Diagnostic tool for CompX/PixArt wireless mouse receivers.

Logs ALL incoming HID packets from your wireless mouse receiver in real-time,
showing the raw bytes alongside our battery parser's interpretation.

Usage:
  python tools/dump_compx_packets.py

Share the output with the developer so we can identify the correct battery byte offset.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import hid
except ImportError:
    print("ERROR: hid module not found. Install it with: pip install hidapi")
    sys.exit(1)

from protocols.compx import COMPX_VIDS, COMPX_DEVICES
from protocols.base import find_hid_device_paths
from protocols.utils import parse_battery_telemetry

BATTERY_RANGE = range(5, 101)  # values we'd consider plausible battery readings

def main():
    print("=" * 70)
    print("  CompX/PixArt Wireless Mouse — Raw HID Packet Diagnostic")
    print("=" * 70)
    print()

    candidates = find_hid_device_paths(COMPX_VIDS, COMPX_DEVICES)
    if not candidates:
        print("No CompX/PixArt wireless mouse receiver found.")
        print("Make sure the USB receiver is plugged in and the mouse is paired.")
        sys.exit(1)

    print(f"Found {len(candidates)} device interface(s):")
    for i, (path, mode, name) in enumerate(candidates):
        print(f"  [{i+1}] {name} | mode={mode} | path={path}")
    print()

    # Open all candidates for passive listening
    open_devs = []
    for path, mode, name in candidates:
        try:
            dev = hid.device()
            dev.open_path(path.encode('utf-8') if isinstance(path, str) else path)
            dev.set_nonblocking(True)
            open_devs.append((path, name, mode, dev))
            print(f"Opened: {name} ({mode})")
        except OSError as e:
            print(f"Could not open {path}: {e}")

    if not open_devs:
        print("ERROR: Could not open any device.")
        sys.exit(1)

    print()
    print("Listening for packets... Move your mouse or press buttons to generate traffic.")
    print("Press Ctrl+C to stop.\n")
    print(f"{'TIME':>8}  {'PATH':<30}  {'RAW BYTES (first 12)':40}  {'PARSER RESULT'}")
    print("-" * 110)

    try:
        while True:
            for path, name, mode, dev in open_devs:
                try:
                    data = dev.read(64)
                    if data:
                        d = list(data)
                        ts = time.strftime("%H:%M:%S")
                        hex_str = " ".join(f"{b:02x}" for b in d[:12])
                        
                        vid = None
                        for e in hid.enumerate():
                            if e['path'] == path:
                                vid = e['vendor_id']
                                break

                        dev_id = d[1] if len(d) > 1 else None
                        batt, charging = parse_battery_telemetry(d, dev_id, is_beken=False, vid=vid)
                        
                        plausible = [f"idx{i}={d[i]}" for i in range(2, min(len(d), 10)) if d[i] in BATTERY_RANGE and d[i] != 0x40]
                        
                        if batt is not None:
                            result = f"✅ battery={batt}% charging={charging}"
                        elif plausible:
                            result = f"⚠️  no parse | plausible bytes: {', '.join(plausible)}"
                        else:
                            result = "— no battery data"

                        short_path = path[-28:] if len(path) > 28 else path
                        print(f"{ts}  {short_path:<30}  [{hex_str}]  {result}")
                except OSError:
                    pass
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n\nStopped. Please copy the above output and share it with the developer.")
    finally:
        for _, _, _, dev in open_devs:
            try:
                dev.close()
            except Exception:
                pass

if __name__ == "__main__":
    main()
