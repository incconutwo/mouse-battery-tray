import time
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure local workspace is in python path
sys.path.insert(0, os.path.abspath("."))

from protocols import get_all_handlers
from protocols.utils import parse_battery_telemetry

class MockApp:
    def __init__(self):
        self.running = True
        self.status = "disconnected"
        self.last_battery = -1
        self.current_model = "Unknown"
        self.last_theme = "dark"
        self.last_update_check_time = time.time()
        self._updates_checked = False

    def update_tray(self):
        pass

    def update_battery_level(self, battery: int, charging: bool = False):
        self.last_battery = battery
        self.status = "charging" if charging else "connected"

    def check_for_updates(self, manual=False):
        pass


class MockHIDDevice:
    def __init__(self, path, test_case):
        self.path = path
        self.test_case = test_case
        self.feature_reports_sent = []
        self.closed = False

    def open_path(self, path):
        pass

    def set_nonblocking(self, mode):
        pass

    def close(self):
        self.closed = True

    def read(self, length):
        # Return programmed telemetry packet once, then empty
        if self.test_case.get("read_packets"):
            return self.test_case["read_packets"].pop(0)
        return []

    def send_feature_report(self, bytes_data):
        self.feature_reports_sent.append(list(bytes_data))

    def get_feature_report(self, report_id, length):
        if self.test_case.get("feature_replies"):
            return self.test_case["feature_replies"].get(report_id, [])
        return []


# Complete Matrix of Test Devices & Simulated Telemetry Packets
TEST_DEVICE_MATRIX = [
    # ---------------------------------------------------------
    # BEKEN PROTOCOL (Attack Shark / Beken OEM)
    # ---------------------------------------------------------
    {
        "name": "Attack Shark X11 (2.4G Wireless)",
        "expected_model": "Attack Shark X11",
        "expected_mode": "wireless",
        "expected_protocol": "BekenProtocol",
        "enum_dicts": [{
            "vendor_id": 0x1d57, "product_id": 0xfa60, "product_string": "2.4G Wireless Receiver",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_1d57&pid_fa60#001"
        }],
        # Simulated Beken packet: [0x03, 0x55 (X11 ID), 0x40, 0x00, 44 (44% batt), ...]
        "read_packets": [[0x03, 0x55, 0x40, 0x00, 44, 0x00, 0x00, 0x00]],
        "expected_batt": 44,
        "disallow_feature_queries": True
    },
    {
        "name": "Attack Shark X6 (2.4G Wireless)",
        "expected_model": "Attack Shark X6",
        "expected_mode": "wireless",
        "expected_protocol": "BekenProtocol",
        "enum_dicts": [{
            "vendor_id": 0x1d57, "product_id": 0xfa62, "product_string": "Attack Shark X6",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_1d57&pid_fa62#001"
        }],
        # Simulated Beken packet: [0x03, 0x85 (X6 ID), 0x40, 0x00, 8 (8*10=80% scaling), ...]
        "read_packets": [[0x03, 0x85, 0x40, 0x00, 8, 0x00, 0x00, 0x00]],
        "expected_batt": 80,
        "disallow_feature_queries": True
    },
    {
        "name": "Attack Shark R1 (Wired Mode)",
        "expected_model": "Attack Shark R1",
        "expected_mode": "wired",
        "expected_protocol": "BekenProtocol",
        "enum_dicts": [{
            "vendor_id": 0x1d57, "product_id": 0xfa61, "product_string": "Attack Shark R1 Wired",
            "interface_number": 0, "usage_page": 1, "path": "\\\\?\\hid#vid_1d57&pid_fa61#001"
        }],
        "read_packets": [],
        "expected_status": "charging",
        "disallow_feature_queries": True
    },

    # ---------------------------------------------------------
    # COMPX / NORDIC PROTOCOL (Pulsar, VXE, Scyrox, Lamzu, G-Wolves, MAMBASNAKE, Hitscan, Cherry Xtrfy, Incott)
    # ---------------------------------------------------------
    {
        "name": "VXE R1 Pro / Pro Max",
        "expected_model": "VXE R1 Pro / Pro Max",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x3554, "product_id": 0xf58a, "product_string": "VXE R1 Pro Receiver",
            "interface_number": 2, "usage_page": 0xff04, "path": "\\\\?\\hid#vid_3554&pid_f58a#001"
        }],
        # Feature report 0x06 reply payload: [0x06, 0x00, 0x00, 0x00, 85 (85% batt), ...]
        "read_packets": [],
        "feature_replies": {6: [0x06, 0x00, 0x00, 0x00, 85, 0x00]},
        "expected_batt": 85
    },
    {
        "name": "Pulsar 8K Dongle Gen.2",
        "expected_model": "Pulsar 8K Dongle Gen.2",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x3710, "product_id": 0x5406, "product_string": "Pulsar 8K Dongle",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_3710&pid_5406#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 92, 0x00]],
        "expected_batt": 92
    },
    {
        "name": "Scyrox V6 8K",
        "expected_model": "Scyrox V6 8K",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x3554, "product_id": 0xf5f7, "product_string": "Scyrox V6 8K Receiver",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_3554&pid_f5f7#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 68, 0x00]],
        "expected_batt": 68
    },
    {
        "name": "Lamzu Maya X 8K",
        "expected_model": "Lamzu Maya X 8K",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x373e, "product_id": 0x001e, "product_string": "Lamzu 8K Dongle",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_373e&pid_001e#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 77, 0x00]],
        "expected_batt": 77
    },
    {
        "name": "G-Wolves Fenrir Pro 8K",
        "expected_model": "G-Wolves Fenrir Pro 8K",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x33e4, "product_id": 0x3854, "product_string": "G-Wolves 8K Dongle",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_33e4&pid_3854#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 55, 0x00]],
        "expected_batt": 55
    },
    {
        "name": "Hitscan Hyperlight 8K",
        "expected_model": "Hitscan Hyperlight",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x3770, "product_id": 0x0300, "product_string": "Hitscan 8K Receiver",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_3770&pid_0300#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 64, 0x00]],
        "expected_batt": 64
    },
    {
        "name": "Cherry Xtrfy M68 Wireless",
        "expected_model": "Cherry Xtrfy M68 Wireless",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x046a, "product_id": 0x0330, "product_string": "M68 Receiver",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_046a&pid_0330#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 90, 0x00]],
        "expected_batt": 90
    },

    # ---------------------------------------------------------
    # WLMOUSE PROTOCOL (WLMouse Beast X)
    # ---------------------------------------------------------
    {
        "name": "WLMouse Beast X Mini Pro",
        "expected_model": "WLMouse Beast X Mini Pro",
        "expected_mode": "wireless",
        "expected_protocol": "WLMouseProtocol",
        "enum_dicts": [{
            "vendor_id": 0x36a7, "product_id": 0xa868, "product_string": "WLMouse Beast X",
            "usage_page": 0xffff, "usage": 0x00, "path": "\\\\?\\hid#vid_36a7&pid_a868#001"
        }],
        # Feature report 0 payload: [0x00, 0x00, 0xa1, 0x00, 0x02, 0x02, 0x00, 0x83, 0x00 (not charging), 72 (72% batt)]
        "read_packets": [],
        "feature_replies": {0: [0x00, 0x00, 0xa1, 0x00, 0x02, 0x02, 0x00, 0x83, 0x00, 72]},
        "expected_batt": 72
    },

    # ---------------------------------------------------------
    # RAZER PROTOCOL (OpenRazer 90-Byte Feature Query)
    # ---------------------------------------------------------
    {
        "name": "Razer DeathAdder V3",
        "expected_model": "Razer DeathAdder V3",
        "expected_mode": "wireless",
        "expected_protocol": "RazerProtocol",
        "enum_dicts": [{
            "vendor_id": 0x1532, "product_id": 0x00b2, "product_string": "Razer DeathAdder V3",
            "usage_page": 0xff00, "usage": 0x01, "path": "\\\\?\\hid#vid_1532&pid_00b2#001"
        }],
        "read_packets": [],
        "feature_replies": {0: [0x00, 0x02, 0x1f, 0x00, 0x03, 0x07, 0x02, 0x00, 65, 0x00] + [0]*80},
        "expected_batt": 65
    },
    {
        "name": "Razer HyperPolling Dongle",
        "expected_model": "Razer HyperPolling Dongle",
        "expected_mode": "wireless",
        "expected_protocol": "RazerProtocol",
        "enum_dicts": [{
            "vendor_id": 0x1532, "product_id": 0x00b3, "product_string": "Razer Dongle",
            "usage_page": 0xff00, "usage": 0x01, "path": "\\\\?\\hid#vid_1532&pid_00b3#001"
        }],
        "read_packets": [],
        "feature_replies": {0: [0x00, 0x02, 0x1f, 0x00, 0x03, 0x07, 0x02, 0x00, 100, 0x00] + [0]*80},
        "expected_batt": 100
    },

    # ---------------------------------------------------------
    # ADDITIONAL BRAND VARIANTS
    # ---------------------------------------------------------
    {
        "name": "Attack Shark X3 (Wired)",
        "expected_model": "Attack Shark X3",
        "expected_mode": "wired",
        "expected_protocol": "BekenProtocol",
        "enum_dicts": [{
            "vendor_id": 0x1d57, "product_id": 0xfa50, "product_string": "Attack Shark X3",
            "interface_number": 0, "usage_page": 1, "path": "\\\\?\\hid#vid_1d57&pid_fa50#001"
        }],
        "read_packets": [],
        "expected_status": "charging",
        "disallow_feature_queries": True
    },
    {
        "name": "Pulsar Xlite / X2 Series",
        "expected_model": "Pulsar X2 / Xlite Series",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x25a7, "product_id": 0xfa7c, "product_string": "Pulsar Receiver",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_25a7&pid_fa7c#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 88, 0x00]],
        "expected_batt": 88
    },
    {
        "name": "Pulsar X2 CrazyLight (Wired)",
        "expected_model": "Pulsar X2 CrazyLight",
        "expected_mode": "wired",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x3710, "product_id": 0x3414, "product_string": "CrazyLight Cable",
            "interface_number": 0, "usage_page": 1, "path": "\\\\?\\hid#vid_3710&pid_3414#001"
        }],
        "read_packets": [],
        "expected_status": "charging"
    },
    {
        "name": "G-Wolves HTX Ultra 8K",
        "expected_model": "G-Wolves HTX Ultra 8K",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x33e4, "product_id": 0x5617, "product_string": "HTX Ultra Dongle",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_33e4&pid_5617#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 48, 0x00]],
        "expected_batt": 48
    },
    {
        "name": "MAMBASNAKE M5 Ultra",
        "expected_model": "Mambasnake M5 Ultra",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x373e, "product_id": 0x0050, "product_string": "M5 Ultra Dongle",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_373e&pid_0050#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 95, 0x00]],
        "expected_batt": 95
    },
    {
        "name": "Incott G24 Pro (8K Dongle)",
        "expected_model": "Incott G24 Pro",
        "expected_mode": "wireless",
        "expected_protocol": "CompxProtocol",
        "enum_dicts": [{
            "vendor_id": 0x093a, "product_id": 0x522c, "product_string": "Incott 8K Receiver",
            "interface_number": 2, "usage_page": 10, "path": "\\\\?\\hid#vid_093a&pid_522c#001"
        }],
        "read_packets": [[0x03, 0x00, 0x40, 0x00, 82, 0x00]],
        "expected_batt": 82
    },
    {
        "name": "WLMouse Beast X",
        "expected_model": "WLMouse Beast X",
        "expected_mode": "wireless",
        "expected_protocol": "WLMouseProtocol",
        "enum_dicts": [{
            "vendor_id": 0x36a7, "product_id": 0xa887, "product_string": "WLMouse Beast X",
            "usage_page": 0xffff, "usage": 0x00, "path": "\\\\?\\hid#vid_36a7&pid_a887#001"
        }],
        "read_packets": [],
        "feature_replies": {0: [0x00, 0x00, 0xa1, 0x00, 0x02, 0x02, 0x00, 0x83, 0x00, 99]},
        "expected_batt": 99
    }
]


def run_simulation_tests():
    print("\n" + "="*80)
    print(" === RUNNING MOUSE SIMULATION & PROTOCOL INTEGRITY TEST SUITE ===")
    print("="*80 + "\n")

    passed_count = 0
    failed_count = 0
    handlers = get_all_handlers()

    for idx, tc in enumerate(TEST_DEVICE_MATRIX, 1):
        test_name = tc["name"]
        print(f"Test #{idx:02d}: {test_name:<40}", end="")

        mock_dev = None

        def mock_enum(vid=None):
            return tc["enum_dicts"]

        def mock_device_factory():
            nonlocal mock_dev
            mock_dev = MockHIDDevice(tc["enum_dicts"][0]["path"], tc)
            return mock_dev

        with patch("hid.enumerate", side_effect=mock_enum), \
             patch("hid.device", side_effect=mock_device_factory):

            matched_handler = None
            found_path = None
            found_mode = None
            found_model = None

            for h in handlers:
                path, mode, model = h.find_device()
                if path:
                    matched_handler = h
                    found_path, found_mode, found_model = path, mode, model
                    break

            if not matched_handler:
                print("[FAILED]: Device not discovered by any protocol handler")
                failed_count += 1
                continue

            handler_class = matched_handler.__class__.__name__
            if handler_class != tc["expected_protocol"]:
                print(f"[FAILED]: Matched protocol {handler_class}, expected {tc['expected_protocol']}")
                failed_count += 1
                continue



            if found_mode != tc["expected_mode"]:
                print(f"[FAILED]: Mode resolved as '{found_mode}', expected '{tc['expected_mode']}'")
                failed_count += 1
                continue

            # Execute 1 iteration of handle_device
            mock_app = MockApp()
            
            # Shorten sleep during test loop
            with patch("time.sleep", return_value=None):
                orig_update_batt = mock_app.update_battery_level
                def wrap_update_batt(batt, charging=False):
                    orig_update_batt(batt, charging)
                    mock_app.running = False

                mock_app.update_battery_level = wrap_update_batt

                try:
                    matched_handler.handle_device(mock_app, found_path, found_mode, found_model)
                except Exception as e:
                    print(f"[FAILED]: Exception in handle_device: {e}")
                    failed_count += 1
                    continue

            # Verify dynamic model name after handle_device resolution
            if mock_app.current_model != tc["expected_model"] and found_model != tc["expected_model"]:
                print(f"[FAILED]: Model resolved as '{mock_app.current_model}', expected '{tc['expected_model']}'")
                failed_count += 1
                continue

            # Verify battery reading
            if "expected_batt" in tc:
                if mock_app.last_battery != tc["expected_batt"]:
                    print(f"❌ FAILED: Extracted battery {mock_app.last_battery}%, expected {tc['expected_batt']}%")
                    failed_count += 1
                    continue

            # Verify protocol safety guards (e.g. no feature reports for Beken)
            if tc.get("disallow_feature_queries") and mock_dev:
                if len(mock_dev.feature_reports_sent) > 0:
                    print(f"[FAILED]: Feature queries were improperly sent to safety-guarded Beken device!")
                    failed_count += 1
                    continue

            print("[PASSED]")
            passed_count += 1

    print("\n" + "="*80)
    print(f" TEST RESULTS SUMMARY: {passed_count}/{len(TEST_DEVICE_MATRIX)} Passed")
    print("="*80 + "\n")

    if failed_count == 0:
        print("ALL PROTOCOL SIMULATIONS VERIFIED SUCCESSFULLY WITH 0 REGRESSIONS!")
        return 0
    else:
        print(f"WARNING: {failed_count} TEST(S) FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(run_simulation_tests())
