# Keypad matrix routing and commissioning driver

2026-10-07. **Engineering checkpoint; fabrication release remains blocked.**

Follow-up: the [ESP32 bring-up application](../../firmware/bringup/README.md) now
integrates this driver and cross-builds for the target. Hardware testing remains
open; the layout results below are unchanged.

All eight matrix branches now connect U2 to the existing 16-switch matrix.
All 64 physical switch contacts and eight controller pins pass independent
connectivity checks. No parts, existing tracks/vias, stackup or design rules
were changed. New fanout uses ordinary 0.5 mm through vias with 0.3 mm drills.
New inner-layer segments avoid the protected USB reference area.

| Function | U2 pin | Switches |
| --- | --- | --- |
| ROW0 | 8 | SW1–SW4, both contacts numbered 1 |
| ROW1 | 7 | SW5–SW8, both contacts numbered 1 |
| ROW2 | 6 | SW9–SW12, both contacts numbered 1 |
| ROW3 | 5 | SW13–SW16, both contacts numbered 1 |
| COL0 | 9 | SW1, SW5, SW9, SW13, both contacts numbered 2 |
| COL1 | 10 | SW2, SW6, SW10, SW14, both contacts numbered 2 |
| COL2 | 11 | SW3, SW7, SW11, SW15, both contacts numbered 2 |
| COL3 | 12 | SW4, SW8, SW12, SW16, both contacts numbered 2 |

`generated/keypad-routing.json` records board hashes, preserved copper,
fanout geometry and route evidence. Before installation, all 621 previously
connected pad groups were compared with the staged board; none lost a connection.
The pre-change board/rules/reports are retained under
`archive/handset-before-keypad-routing/24e35cd12f1f/` at the repository root.

The saved checkpoint has zero native DRC violations and zero schematic parity
findings. Unconnected items drop from 258 to 250. There are still 30 ERC findings
and 11 open engineering blocker groups. The main check script runs the eight
matrix groups, five routing regression cases and the host firmware tests,
alongside the prior core, USB, display, expansion and power checks.

The [keypad driver](../../firmware/keypad/README.md) decodes all 16 switches,
checks configuration, bounds FIFO draining and invalidates application key
state after overflow, transfer failure or unexpected events. Its 12 host-test
scenarios do not establish operation on the ESP32 or physical handset.
It does not program GPIO outputs or enable the backlight, modem or media rails.
Target HAL/application integration and shared U2 GPIO sequencing remain open.

After overall hardware approval, commission each switch individually with
press and release logging, then measure IRQ/service timing and test reset,
disconnection and overflow recovery. Check required multi-key combinations:
the current matrix has no per-key diodes and does not establish ghost-free
arbitrary rollover. Key legends, user-interface actions, enclosure actuation,
EMI and switch debounce behavior still require qualification.
