Attack Shark Battery Tray 1.2.0
================================

This small Windows notification-area app displays the live battery percentage
reported by compatible Attack Shark/Beken wireless mice. The Attack Shark X11
has been verified with its 2.4 GHz USB receiver.

USING THE APP

1. Put the mouse in 2.4G mode and connect its receiver.
2. Start "Attack Shark Battery Tray" from the Start menu.
3. Move the mouse. Its percentage appears as a coloured number under the
   taskbar notification-area arrow (^).
4. Right-click the number to enable or disable "Start with Windows", open the
   source project, or exit.

DISPLAY

- Green: 50% or higher
- Orange: 20-49%
- Red: below 20%
- Chg: wired/charging mode detected
- --: waiting for the mouse to send a battery packet
- ??: receiver not detected

PRIVACY AND NETWORK ACCESS

The app reads the local USB HID receiver and the current user's Windows startup
registry value. It does not transmit telemetry. It only opens a web browser if
you explicitly choose "Open source project" from its menu.

SOURCE AND LICENSE

Source: https://github.com/subok911/attack-shark-battery-tray
Upstream: https://github.com/incconutwo/attack-shark-battery-tray
License: MIT. See LICENSE.txt installed alongside the application.
Original copyright (c) 2026 incconu_two.

This is a community build and is not affiliated with or endorsed by Attack
Shark. The installer and application are not code-signed, so Windows may show a
SmartScreen warning. Verify the SHA-256 checksums supplied with the installer.
