# Mouse Battery Tray Indicator

[![Platform](https://img.shields.io/badge/Platform-Windows_10_%7C_11-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/incconutwo/mouse-battery-tray)
[![Release](https://img.shields.io/github/v/release/incconutwo/mouse-battery-tray?style=for-the-badge&color=28a745)](https://github.com/incconutwo/mouse-battery-tray/releases)
[![Downloads](https://img.shields.io/github/downloads/incconutwo/mouse-battery-tray/total?style=for-the-badge&color=7952b3)](https://github.com/incconutwo/mouse-battery-tray/releases)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Ko-fi](https://img.shields.io/badge/Support_on-Ko--fi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/incconutwo)

<img src="https://github.com/user-attachments/assets/4e384838-6073-4457-827c-737c18f909f2" alt="Mouse Battery Tray Screenshot" width="150" align="right">

A lightweight, standalone Windows system tray application that displays the live battery percentage of wireless gaming mice (Attack Shark, Pulsar, WLMouse Beast X family, Beken/CompX OEM, etc.) directly in the taskbar.

[<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 4px;"><path d="M12 15V3"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/></svg> **Download Latest Release (MouseBatteryTray.exe)**](https://github.com/incconutwo/mouse-battery-tray/releases/latest)

This tool serves as a lightweight alternative to resource-heavy official manufacturer hub software.

---

## Supported Devices Status

The application officially recognizes the following models, with dynamic fallback support for compatible OEM mice:

| Brand | Model | 2.4G Wireless | Wired / Charging | Notes |
| :--- | :--- | :---: | :---: | :--- |
| **WLMouse** | Beast X / Mini Pro | 🟢 | 🟢 | 8K Receiver (`VID 0x36a7`) |
| **Attack Shark** | X11 / X6 / R1 / X3 | 🟢 | 🟢 | Dynamic model resolution |
| **Pulsar** | Xlite / X2 Series | 🟢 | 🟢 | CompX OEM |
| | 8K Dongle Gen.2 | 🟢 | 🟡 | 8K Dongle (`VID 0x3710`) |
| **VXE** | R1 Series (R1 / SE / SE+) | 🟢 | 🟢 | Dongles (`VID 0x3554`, `0x320f`, `0x3537`) |
| **Incott** | G24 Pro | 🟢 | 🟢 | PixArt 8K Dongle (`VID 0x093a`) |
| **Hitscan** | Hyperlight | 🟢 | 🟡 | 8K Dongle (`VID 0x3770`) |
| **Generic** | Other Beken / CompX / WLMouse | 🟡 | 🟡 | Dynamic OEM fallback |

> **Status Key:** 🟢 Supported & Verified &nbsp;|&nbsp; 🟡 Auto-Detected / Untested

---

## Contributing & Adding New Models

If your mouse is not fully recognized or is displayed as a generic device, we would love to add official support for it! 

We've made this process incredibly easy by including a standalone **Hardware ID Extractor wizard** (`dump_devices.exe`):

1. Go to the [Releases page](https://github.com/incconutwo/mouse-battery-tray/releases) and download **`dump_devices.exe`** (or run `python dump_devices.py`).
2. Run it and follow the simple 2-step prompt to scan your mouse in **Wireless (2.4G)** and **Wired** modes.
3. The wizard will automatically generate the clean Python dictionary configuration lines for your device.
4. Copy the generated block and paste it into a GitHub issue or Reddit reply!

If you want to manually add support yourself, you can simply append your Product ID to the `SUPPORTED_DEVICES` or `WLMOUSE_DEVICES` dictionary in `devices.py`:

```python
SUPPORTED_DEVICES = {
    0xYOUR_PID_HEX: ("Your Mouse Name", "wireless"),
}
```

---

## Features

- **Live Numeric Percentage:** Displays the exact battery level directly on the tray icon as a colored number.
- **Color-Coded Status:**
  - 🟢 **Green** ($\ge 50\%$) - Healthy charge
  - 🟠 **Orange** ($20\% - 49\%$) - Moderate charge
  - 🔴 **Red** ($< 20\%$) - Low battery (time to charge)
- **Auto Taskbar Theme Detection:** Automatically adapts icon colors and contrast for Windows **Light Mode** and **Dark Mode** taskbars without extra configuration options.
- **Intelligent Hours Estimate:** Real-time battery discharge slope tracking with minimalistic tooltip predictions (e.g., `Mouse: 85% (~12h)` or `42% (~4h 30m)`), complete with a menu toggle.
- **Configurable Low Battery Alerts:** Sends a Windows toast notification when battery reaches your chosen threshold (25%, 20%, 15%, 10%, or Disabled).
- **Update Checker:** Asynchronously checks for new releases on GitHub directly from the right-click tray menu (`Check for Updates`).
- **Clean Connection & Charging States:** Displays **`Chg`** (blue) while charging, **`--`** (grey) while awaiting initial reading, and **`??`** when disconnected.
- **Start with Windows Toggle:** Right-click the icon to toggle startup behavior. It writes directly to your user registry (`HKCU`), requiring **zero Administrator (UAC) prompts**.
- **Multi-Brand Compatibility:** Supports Beken-OEM firmware (`VID: 0x1d57`), CompX/Pulsar (`VID: 0x25a7`, `0x3710`), and WLMouse (`VID: 0x36a7`).


---

## Installation

### Prerequisites
Make sure you have [Python 3.10+](https://www.python.org/) installed and added to your system PATH.

### Install Dependencies
Open your terminal (Command Prompt or PowerShell) and run:
```bash
pip install hidapi pystray pillow
```

---

## How to Run

1. **Run in Background (Recommended):**
   Run the file using `pythonw` (or double-click the `.pyw` extension) to start it silently in the background:
   ```bash
   pythonw battery_tray.pyw
   ```
2. **Run in Terminal (Debugging):**
   If you want to view console logs:
   ```bash
   python battery_tray.pyw
   ```

---

## Troubleshooting

- **Icon Stays on `??`:** 
  Ensure the mouse is turned on, in wireless mode (using the 2.4G adapter), and not asleep. Wake the mouse by moving it around for the first battery status packet to transmit.
- **Permissions Issue:**
  The app runs entirely in user-space and does not require admin rights. If the tray icon doesn't update, check if another exclusive tool (like the official software) is currently open and locking the USB receiver port.

---

## Acknowledgments & Credits

Special thanks to all community members who contributed device ID mappings and hardware dumps:

- **[@len0c](https://github.com/len0c)** – Reverse-engineered HID protocol handling and initial integration for the **WLMouse Beast X** series.
- **[@HarukaYamamoto0](https://github.com/HarukaYamamoto0)** – Shared additional Beken OEM model device ID mappings ([attack-shark-x11-driver](https://github.com/HarukaYamamoto0/attack-shark-x11-driver)).
- **[@CptNinja](https://github.com/CptNinja)** – Provided hardware ID dump for the **Pulsar 8K Dongle Gen.2** (`VID 0x3710`, `PID 0x5406`).
- **[@nzeck1](https://github.com/nzeck1)** – Provided hardware ID dump for the **VXE R1 Series** (R1 / R1 SE / R1 SE+).
- **[@Vinsmok3](https://github.com/Vinsmok3)** – Provided hardware ID dump for the **Hitscan Hyperlight** (`VID 0x3770`, `PID 0x0300`).
- **u/Monophonotronic** – Provided hardware ID dump for the **Incott G24 Pro** (`VID 0x093a`, `PID 0x522c` / `0x622c`).
- **u/djnemoson** – Provided hardware ID dump for the **Pulsar X2 Wireless** (`VID 0x25a7`, `PID 0xfa7c` / `0xfa7b`).
- **TwistedVincenzo** – Provided hardware ID dump for the **Pulsar Xlite Wireless**.
