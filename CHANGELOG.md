# Changelog

All notable changes to the Mouse Battery Tray project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.2.2] - 2026-07-25

### 🚀 New Device Support & Protocols

- **Razer Universal Wireless Support:** Added Razer mouse support (`VID 0x1532`) featuring OpenRazer 90-byte Feature Report active querying (`Class 0x07`, `Command 0x02` with XOR checksum calculation). Supports **Razer HyperPolling Wireless Dongle** (`PID 0x00b3`) and all modern wireless Razer mice out-of-the-box via dynamic PID fallback.
- **Pulsar X2 Series:** Added mapping for **Pulsar X2 Wireless** (`VID 0x25a7`, `PID 0xfa7c` / `0xfa7b`).
- **Incott G24 Pro:** Added mapping for **Incott G24 Pro** (`VID 0x093a`, `PID 0x522c` / `0x622c`) and broadened `0x03` battery report matching for PixArt 8K telemetry packets.
- **VXE R1 Series Optimization:** Prioritized HID Endpoint 2 / Usage Page 10 for VXE R1, R1 SE, and R1 SE+ to resolve "Waiting for battery reading..." delays.

### 🐛 Bug Fixes & Stability Improvements

- **PC-Sleep Gap & Hours Estimation Overhaul:** Fixed PC sleep detection to track time between polling loops instead of time between battery drops. Battery percentage drops now anchor and estimate remaining hours accurately without false resets.
- **Non-Mouse Peripheral Filter:** Added strict HID filtering in `devices.py` to ignore keyboards, microphones, and USB audio dongles sharing standard VIDs (e.g. `0x258a`), resolving false "Gaming Keyboard" detection.
- **Auto-Switching on Receiver Re-plug:** Fixed polling loop to detect device path changes (`path_check != path`), allowing the app to seamlessly auto-switch when receivers are re-plugged or mice are reconnected.
- **Attack Shark X6 Battery Scale Fix:** Restricted 10x battery scaling multiplier exclusively to X6 firmware (`device_id 0x85`), preventing standard mice from jumping to 100% when reaching 10% battery.
- **False Dock Charging State (`Chg`) Guard:** Restricted non-zero byte checks to confirmed Beken devices to prevent movement packets from false-triggering `Chg` status on VXE / Hitscan mice.

### 🎨 Documentation & UI

- **Tray Menu Clean-up:** Updated tray context menu item to clean text `"Donate / Support"`.
- **README Enhancements:** Added modern Shields.io header badges (Platform, Release, Downloads, License, Ko-fi) and a direct Download button featuring a Lucide SVG download icon.
- **Community Credits:** Added acknowledgments for **u/MarcBelmaati**, **u/Monophonotronic**, **u/djnemoson**, **@nzeck1**, **@Vinsmok3**, and community contributors.
- **GitHub Sponsor Integration:** Created `.github/FUNDING.yml` for native GitHub sponsorship support.

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
