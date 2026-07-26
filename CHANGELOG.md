# Changelog

All notable changes to the Mouse Battery Tray project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.2.2] - 2026-07-26

### 🚀 New Device Support & Protocol Engines

- **FeikoWielsma Code Contribution & VXE R1 Pro/Max Support:** Full battery reading support for **VXE R1 Pro** and **VXE R1 Pro Max** (`VID 0x3554, PID 0xf58a` / `VID 0x320f, PID 0x5055`). Special credit and thanks to **FeikoWielsma** (from PR #6 / `mouse-battery-tray-feat-vxe-r1-pro-support`) for contributing the initial VXE R1 Pro mapping, `usage_page == 0xff04` endpoint prioritization, and Feature Report `0x06` fallback polling!
- **Razer Universal Wireless & DeathAdder V3 Support:** Added Razer mouse support (`VID 0x1532`) featuring OpenRazer 90-byte Feature Report active querying (`Class 0x07`, `Command 0x02` with XOR checksum calculation). Supports **Razer DeathAdder V3** (`PID 0x00b2`), **Razer HyperPolling Wireless Dongle** (`PID 0x00b3`), and all modern wireless Razer mice out-of-the-box via dynamic PID fallback.
- **Expanded Mouse Model Database:** Mapped hardware product IDs for 10 new mouse families:
  - **Scyrox V6 8K** (`VID 0x3554, PID 0xf5f7`) - Thanks to u/SadPeppermint
  - **Lamzu Maya X 8K** (`VID 0x373e, PID 0x001e`) - Thanks to u/kaklikesmilfs
  - **G-Wolves Fenrir Pro 8K & HTX Ultra 8K** (`VID 0x33e4, PIDs 0x3854, 0x3619, 0x5617, 0x5608`) - Thanks to u/Kbphan & u/touholic
  - **MAMBASNAKE M5 Ultra** (`VID 0x373e, PIDs 0x0050, 0x0051`) - Thanks to u/touholic
  - **Pulsar X2 & X2N CrazyLight Series** (`VID 0x3710, PIDs 0x3414, 0x3510`) - Thanks to u/touholic & u/guadygood
  - **Hitscan Hyperlight 1K & 8K** (`VID 0x3770, PIDs 0x0300, 0x0200`) - Thanks to @Vinsmok3 & @lilldizzy
  - **Cherry Xtrfy M68 Wireless** (`VID 0x046a, PIDs 0x0330, 0x0334`) - Thanks to u/Truth_Lies & @kidguyperson
  - **Attack Shark 8K Receiver** (`VID 0x1d57, PID 0xfa65`)
  - **Pulsar X2 Series** (`VID 0x25a7, PIDs 0xfa7c, 0xfa7b`) - Thanks to u/djnemoson & TwistedVincenzo
  - **Incott G24 Pro** (`VID 0x093a, PIDs 0x522c, 0x622c`) - Thanks to u/Monophonotronic

### 🛠 Protocol Engine & Architectural Upgrades

- **Multi-Endpoint Candidate Discovery:** Created `find_device_paths()` in `devices.py` to discover and open all candidate HID sub-interfaces simultaneously, resolving multi-endpoint 8K receiver delays.
- **CompX / VXE Feature Report `0x06` Fallback Polling:** Implemented active Feature Report `0x06` querying and `get_feature_report` response polling on Windows feature-only endpoints when direct `dev.read()` returns an `OSError` *(code contributed by FeikoWielsma)*.
- **Broadened Telemetry Parser with False-Positive Guard:** Added multi-index candidate byte checks (`4, 2, 3, 5, 1, 6, 7`) with a strict plausibility guard requiring `16% <= val <= 100%` and skipping `0x40` protocol marker bytes to prevent random false battery values.
- **Dynamic Cable / Wired Mode Detection:** Dynamically switches tray status to **Charging / Wired** whenever `"wired"` is present in the USB product string.
- **Razer Protocol Routing Fix:** Removed `RAZER_VID` (`0x1532`) from standard scanner lists to guarantee Razer devices route cleanly to `find_razer()` active OpenRazer querying without passive scanner interception.
- **False Game Controller Mapping Cleanup:** Removed `0x3537:0x2106` (Zikway game controller) from `SUPPORTED_DEVICES` to prevent wireless controllers from falsely being identified as VXE mice.

### 🐛 Bug Fixes & Stability Improvements

- **PC-Sleep Gap & Hours Estimation Overhaul:** Fixed PC sleep detection to track time between polling loops instead of time between battery drops. Battery percentage drops now anchor and estimate remaining hours accurately without false resets.
- **Non-Mouse Peripheral Filter:** Added strict HID filtering in `devices.py` to ignore keyboards, microphones, and USB audio dongles sharing standard VIDs (e.g. `0x258a`), resolving false "Gaming Keyboard" detection.
- **Auto-Switching on Receiver Re-plug:** Fixed polling loop to detect device path changes (`path_check != path`), allowing the app to seamlessly auto-switch when receivers are re-plugged or mice are reconnected.
- **Attack Shark X6 Battery Scale Fix:** Restricted 10x battery scaling multiplier exclusively to X6 firmware (`device_id 0x85`), preventing standard mice from jumping to 100% when reaching 10% battery.

### 🎨 Documentation & Community

- **Community & PR Credits:** Added explicit credit to **FeikoWielsma** (PR #6), **u/Truth_Lies**, **@kidguyperson**, **@lilldizzy**, **u/SadPeppermint**, **u/kaklikesmilfs**, **u/Kbphan**, **u/touholic**, and **u/guadygood**.
- **README Overhaul:** Updated `README.md` with complete 14+ model compatibility matrix and extended community acknowledgments.

---

## [v1.2.1] - 2026-07-24

### 🐛 Bug Fixes & Improvements

- **Hours Estimation Persistence & Anchor Fix:** Fixed a list length bug preventing estimation tooltips from rendering, and added Windows Registry persistence (`HKCU\Software\MouseBatteryTray`) so battery history and drop anchors survive PC reboots and app restarts.
- **Attack Shark X11 & X6 Wireless Dock Charging (`Chg`):** Added active detection for wireless charging dock flags (`data[3] in (0x02, 0x03, 0x80)` and bytes 5-7) so docking the mouse immediately displays **`Chg`**.
- **X6 1-10 Battery Scaling:** Corrected 1-10 scale readings (where 10 = 100%) for Attack Shark X6 firmware.

---

## [v1.2.0] - 2026-07-24

### 🚀 Major Highlights

- **Multi-Brand Mouse Support:** Expanded beyond Attack Shark X11 to support **WLMouse Beast X** series, **Pulsar** series, **VXE R1** series, andgeneric Beken/CompX OEM dongles.
- **Modular Codebase Architecture:** Completely refactored the legacy monolithic script into maintainable modules (`config.py`, `devices.py`, `icon_drawer.py`, `updater.py`, `battery_tray.pyw`).
- **Windows Taskbar Light/Dark Mode Support:** Automatic real-time taskbar theme detection with optimized icon contrast for both Light and Dark Windows themes.
- **Intelligent Battery Remaining Time Estimation:** Real-time discharge rate tracking with tooltip estimates (e.g. `~12h 30m`), complete with sleep/idle gap filtering.
- **Low Battery Toast Notifications:** Native Windows toast alerts triggered when battery level crosses customizable thresholds (25%, 20%, 15%, 10%, or Disabled).

---

### ✨ New Features

- **WLMouse Protocol Engine (`devices.py`):** Added active HID feature report polling (`0x83` query) and passive heartbeat packet parsing for WLMouse Beast X & Beast X Mini Pro (8K receiver support).
- **Expanded Device Database:** Mapped hardware product IDs for:
  - Attack Shark: X11, X11 Pro, X11 SE, X6, X3, R1
  - Pulsar: Xlite Wireless, 8K Dongle Gen.2
  - VXE: R1 / R1 SE / R1 SE+ (CompX/Evision/Zikway dongles)
- **Automatic Update Checker (`updater.py`):** Asynchronous GitHub release checking with semver comparison. Users can check manually or receive background prompts when updates are published.
- **Single Instance Guard (`config.py`):** Named Windows Mutex (`MouseBatteryTray_SingleInstance_Mutex`) prevents multiple app instances from running simultaneously.
- **Memory & RAM Optimization:** Added periodic Python garbage collection (`gc.collect()`), Windows working set trimming (`SetProcessWorkingSetSize`), and Image/Font handle caching.
- **Enhanced Tray Visual Indicators:** Distinct visual states:
  - `Chg` (Blue): Battery charging / wired connection
  - `--` (Grey): Connected, awaiting initial status packet
  - `??` (Grey): Disconnected / Receiver unplugged
  - `?` (Purple): Device detected, battery reading unsupported

---

### 🛠 Refactoring & Internal Improvements

- **Renamed Main Entrypoint:** Transitioned from `x11_battery_tray.pyw` to `battery_tray.pyw` for universal branding.
- **Registry Management (`config.py`):** Native Windows registry persistence (`HKCU\Software\MouseBatteryTray`) for user settings (alert threshold, hours estimate toggle) without requiring administrator rights.
- **Zero-UAC Windows Autostart:** Clean startup key registration (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) supporting both Python interpreter runs and frozen executables.
- **Thread-Safe Architecture:** Background HID polling, UI event loop, and HTTP update checks run on separate threads.

---

### 📦 Build & Hardware Extraction Tools

- **PyInstaller Build Spec (`MouseBatteryTray.spec`):** Added standalone `.exe` build configuration.
- **Hardware ID Extractor Wizard (`dump_devices.py`):** Interactive 2-step prompt for users to capture wireless and wired HID payloads for easy community device submissions.

---

### 📚 Documentation

- **Updated README.md:** Included comprehensive compatibility matrix, step-by-step installation instructions, troubleshooting tips, and contributor guidance.
