# Attack Shark Battery Tray

A lightweight Windows notification-area application that displays the live
battery percentage reported by compatible Attack Shark and Beken-based wireless
mice. The Attack Shark X11 is verified with its 2.4 GHz USB receiver.

This repository is a community-maintained fork of
[incconutwo/attack-shark-battery-tray](https://github.com/incconutwo/attack-shark-battery-tray).
It adds a repeatable installer build with pinned dependencies, single-instance protection, accurate
startup status, packaging metadata, CI, security documentation, and complete
open-source attribution.

The project is not affiliated with or endorsed by Attack Shark.

## Features

- Live numeric battery percentage in the Windows notification area.
- Green, orange, and red status colours based on charge level.
- Charging/wired, waiting, and disconnected states.
- Optional per-user launch at sign-in; no administrator rights required.
- Single-instance protection.
- No telemetry or background network requests.
- Fully open-source Windows installer build with pinned dependencies.

## Supported devices

| Mouse | 2.4 GHz | Wired/charging | Notes |
|---|:---:|:---:|---|
| Attack Shark X11 | Yes | Yes | Verified and fully mapped |
| Attack Shark X6 | Yes | Yes | Verified and fully mapped upstream |
| Attack Shark R1 | Auto-detected | Yes | Wireless endpoint uses generic fallback |
| Attack Shark X3 | Auto-detected | Yes | Wireless endpoint uses generic fallback |
| Other Beken OEM mice (`VID 0x1d57`) | Best effort | Best effort | Generic endpoint fallback |

## Install and use

Download the latest installer from this repository's Releases page.

1. Put the mouse in 2.4G mode and connect its USB receiver.
2. Start **Attack Shark Battery Tray** from the Start menu.
3. Move the mouse to trigger its first battery packet.
4. Find the coloured number under the taskbar notification-area arrow (`^`).
5. Right-click the number to toggle **Start with Windows** or exit.

The display uses these states:

- Green: 50% or higher.
- Orange: 20-49%.
- Red: below 20%.
- `Chg`: wired/charging mode detected.
- `--`: waiting for a battery packet.
- `??`: compatible receiver not detected.

The official mouse software can claim the same HID endpoint. Close it if this
application cannot receive battery packets.

## Run from source

Requirements: Windows 10 or 11 and Python 3.11.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\pythonw.exe .\x11_battery_tray.pyw
```

## Reproducible build

The build contains only the source in this repository and the pinned
open-source dependencies listed in `requirements-build.txt` and
`THIRD_PARTY_NOTICES.md`.

Install Inno Setup 6, then run:

```powershell
winget install --id JRSoftware.InnoSetup -e
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

To build only the standalone PyInstaller application:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1 -SkipInstaller
```

GitHub Actions repeats the same build on a clean Windows runner, verifies the
immutable Inno Setup compiler download by SHA-256, and uploads the unsigned
installer plus checksum as a workflow artifact. Code signing will be integrated
through SignPath if the project is accepted by SignPath Foundation.

## Privacy and security

The application reads local USB HID input reports and its own per-user Windows
startup registry value. It does not collect telemetry or transmit device data.
It opens a browser only when the user selects **Open source project**.

Please report vulnerabilities through GitHub private vulnerability reporting.
See `SECURITY.md`.

## Adding another mouse

Run `dump_devices.py` and follow its wireless and wired scanning prompts. Add
confirmed product IDs to `SUPPORTED_DEVICES` in `x11_battery_tray.pyw` and open
a pull request with the captured endpoint details.

## License and attribution

MIT License. Original copyright (c) 2026 incconu_two. Modifications are
distributed under the same license. See `LICENSE` and
`THIRD_PARTY_NOTICES.md`.
