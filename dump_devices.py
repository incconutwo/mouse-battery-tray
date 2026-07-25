import sys
import time
import hid

def get_mouse_devices():
    devices = hid.enumerate()
    matches = []
    seen = set()
    for d in devices:
        vid = d['vendor_id']
        pid = d['product_id']
        prod = d.get('product_string') or "Unknown Device"
        mfg = d.get('manufacturer_string') or "Unknown Manufacturer"
        
        # Unique key for this specific endpoint interface
        key = (vid, pid, prod, d['interface_number'], d['usage_page'], d['usage'])
        if key in seen:
            continue
            
        prod_lower = prod.lower()
        is_relevant_brand = vid in [0x1d57, 0x25a7, 0x3710, 0x258a, 0x0c45, 0x093a, 0x24ae, 0x1bcf, 0x046d, 0x1532, 0x10f5]
        is_generic_input = any(term in prod_lower for term in ["mouse", "keyboard", "wireless", "receiver", "dongle", "usb", "hid"])
        
        if is_relevant_brand or is_generic_input:
            seen.add(key)
            matches.append({
                'vid': vid,
                'pid': pid,
                'product': prod,
                'mfg': mfg,
                'interface': d['interface_number'],
                'usage_page': d['usage_page'],
                'usage': d['usage']
            })
    return matches

def main():
    print("=" * 65)
    print("       ATTACK SHARK & OEM MOUSE HARDWARE ID EXTRACTOR")
    print("=" * 65)
    print("This tool will guide you to extract your mouse's Hardware IDs")
    print("so the developer can add support for it in the battery tray app.")
    print()
    
    # Step 1: Wireless Mode
    print("[STEP 1 of 2: Wireless Mode]")
    print(" 1. Make sure your mouse is in wireless mode (using the 2.4G USB receiver).")
    print(" 2. Move or click the mouse to wake it up.")
    input("Press Enter when ready to scan...")
    print("Scanning...")
    wireless_devs = get_mouse_devices()
    print(f"Done. Found {len(wireless_devs)} potential wireless endpoints.\n")
    
    # Step 2: Wired Mode
    print("[STEP 2 of 2: Wired Mode]")
    print(" (Note: If you cannot easily connect your mouse via cable, you can skip this step,")
    print("  but capturing the wired ID helps make the software 100% complete!)")
    print(" 1. Unplug the 2.4G wireless USB receiver from your PC.")
    print(" 2. Plug your mouse directly into the PC using its USB charging cable.")
    input("Press Enter when ready to scan...")
    print("Scanning...")
    wired_devs = get_mouse_devices()
    
    # Check if the scan output is identical to Step 1 (meaning the user didn't plug it in)
    wireless_keys = {(w['vid'], w['pid']) for w in wireless_devs}
    wired_keys = {(wd['vid'], wd['pid']) for wd in wired_devs}
    
    if wireless_keys == wired_keys and wireless_keys:
        print("\n[!] Warning: The detected devices are identical to the wireless scan.")
        print("    Did you forget to plug in the USB cable or unplug the receiver?")
        print("    Let's try one more time. Please plug in the cable and unplug the receiver.")
        input("Press Enter to scan again (or press Enter to skip and continue)...")
        print("Scanning...")
        wired_devs = get_mouse_devices()
        
    print(f"Done. Found {len(wired_devs)} potential wired endpoints.\n")
    
    print("=" * 65)
    print("                            RESULTS")
    print("=" * 65)
    print("Please copy and paste the entire block below into your reply:\n")
    print("```python")
    print("# === Discovered Device Info ===")
    
    # Format and display Wireless Candidates (deduplicated by VID/PID)
    print("# Wireless Mode Candidates:")
    printed_wireless = set()
    for w in wireless_devs:
        vid_hex = f"0x{w['vid']:04x}"
        pid_hex = f"0x{w['pid']:04x}"
        
        code_key = (w['vid'], w['pid'])
        if code_key not in printed_wireless:
            printed_wireless.add(code_key)
            clean_name = w['product'] if w['product'] != "2.4G Wireless Device" else "Attack Shark Mouse"
            print(f"# {w['product']} ({w['mfg']}): VID={vid_hex}, PID={pid_hex}")
            print(f"    {pid_hex}: (\"{clean_name}\", \"wireless\"),")
            
    print("\n# Wired Mode Candidates:")
    printed_wired = set()
    for wd in wired_devs:
        vid_hex = f"0x{wd['vid']:04x}"
        pid_hex = f"0x{wd['pid']:04x}"
        
        code_key = (wd['vid'], wd['pid'])
        if code_key not in printed_wired:
            printed_wired.add(code_key)
            print(f"# {wd['product']} ({wd['mfg']}): VID={vid_hex}, PID={pid_hex}")
            print(f"    {pid_hex}: (\"{wd['product']}\", \"wired\"),")
            
    print("```")
    print("\nThank you for helping us improve the tool!")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error occurred: {e}")
        input("\nPress Enter to exit...")
