from typing import Optional, Tuple, List

# VIDs whose devices are known to send config/polling-rate packets that mimic battery packets.
# For these VIDs, we only trust the canonical 0x03/0x40 telemetry packet structure.
STRICT_TELEMETRY_VIDS = {
    0x093a,  # Incott / PixArt — config packets have polling rate at idx 4, misread as battery
    0x33e4,  # G-Wolves — status packets have non-battery bytes at idx 4, misread as battery
}

def parse_battery_telemetry(
    data: List[int],
    device_id: Optional[int] = None,
    is_beken: bool = False,
    vid: Optional[int] = None,
) -> Tuple[Optional[int], Optional[bool]]:
    """Shared telemetry parser for standard packets.
    
    Args:
        data: Raw HID packet bytes.
        device_id: Byte at data[1], used for device-specific scaling.
        is_beken: True for Beken OEM devices (different charging detection).
        vid: Vendor ID — enables per-vendor strict-mode filtering.
    """
    if not data or len(data) < 3:
        return None, None

    report_id = data[0]
    VALID_REPORT_IDS = {0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x10, 0x11, 0x83, 0x84, 0xef}
    if report_id not in VALID_REPORT_IDS:
        return None, None

    # Reject static string descriptor feature reports (e.g. Pulsar 8K Dongle Gen.2 "ongle Gen.2" report)
    if report_id == 0x06 and len(data) >= 6 and data[3:6] == [0x64, 0x64, 0x64]:
        return None, None

    # --- Canonical 0x03/0x40 telemetry packet (highest confidence) ---
    if report_id == 0x03 and len(data) >= 5 and data[2] == 0x40:
        raw_batt = data[4]
        
        if device_id == 0x85 and 0 < raw_batt <= 10:
            batt = raw_batt * 10
        else:
            batt = raw_batt

        if is_beken:
            is_charging = bool(
                data[3] in (0x02, 0x03, 0x80) or
                (len(data) >= 6 and data[5] != 0) or
                (len(data) >= 7 and data[6] != 0) or
                (len(data) >= 8 and data[7] != 0)
            )
        else:
            is_charging = data[3] in (0x02, 0x03, 0x80)

        if 0 <= batt <= 100:
            return batt, is_charging

    # For VIDs known to send ambiguous config packets, bail out after the canonical check.
    # This prevents polling-rate or status bytes from being misread as battery level.
    if vid in STRICT_TELEMETRY_VIDS:
        return None, None

    # --- Generic fallback scan ---
    # Index 1 is typically the device ID. Index 3 is typically charging/subtype status.
    # We remove them from candidates to prevent false positive battery readings (like 0x10 Dev ID = 16%).
    candidate_indices = [4, 2, 5, 6, 7]
    for idx in candidate_indices:
        if idx < len(data):
            val = data[idx]
            if 0x10 <= val <= 100 and val != 0x40:
                sub_type = data[3] if len(data) > 3 else 0
                is_charging = sub_type in (0x02, 0x03, 0x80)
                if device_id == 0x85 and 0 < val <= 10:
                    val = val * 10
                return val, is_charging

    return None, None
