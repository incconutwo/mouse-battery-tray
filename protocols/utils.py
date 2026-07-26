from typing import Optional, Tuple, List

def parse_battery_telemetry(data: List[int], device_id: Optional[int] = None, is_beken: bool = False) -> Tuple[Optional[int], Optional[bool]]:
    """Shared telemetry parser for standard packets"""
    if not data or len(data) < 3:
        return None, None

    report_id = data[0]
    VALID_REPORT_IDS = {0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x10, 0x11, 0x83, 0x84, 0xef}
    if report_id not in VALID_REPORT_IDS:
        return None, None

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

    # Index 1 is typically the device ID. Index 3 is typically charging status.
    # We remove them from candidates to prevent false positive battery readings (like 0x10 Dev ID being read as 16%).
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
