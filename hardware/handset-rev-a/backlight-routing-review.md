# Backlight current driver and routing — 2026-10-01

The CAT4004A backlight circuit is installed and routed. All nine continuity groups pass; native KiCad checks show no new ERC or DRC findings. Electrical, thermal and firmware qualification remain open.

## Circuit

U32 (CAT4004AHU2-GT3), R82 (4.99 kΩ ±1%) and C90 (1 µF X7R, 25 V) replace the previously unrouted Q2 and R52–R55. Four independent sinks connect to J26's LED cathodes. R56/R57 retain the series control resistor and default-off pull-down. The schematic, native PCB, connectivity specification, placement table, custom footprint and `generated/backlight-bom.csv` record the new parts. The older resistor BOM/update reports are historical, superseded artifacts.

The [onsemi CAT4002A/CAT4004A datasheet, revision 3](https://www.onsemi.com/download/data-sheet/pdf/cat4002a-d.pdf), pages 1–3 and 5–10, supports the pin map, current-setting equation, control requirements and package geometry. The 4.99 kΩ setting gives approximately 15 mA per channel, 60 mA total. This is a typical value, not a guaranteed upper bound. The executable screening calculation combines the maximum RSET voltage, resistor tolerance and channel mismatch but leaves absolute current and qualified input demand unknown because gain and temperature variation are not bounded by that calculation.

Firmware must initialize U2's control low for at least 10 ms, then hold it high for full-scale current. EN/DIM counts pulses; ordinary PWM is unsuitable. Dimming remains disabled pending timing qualification. LED-short heating, exposed-pad assembly, supply transients and actual panel behavior remain unqualified; thermal shutdown is not a normal operating-temperature target.

## Routing and preservation

The routing connects the four cathodes, driver supply/bypass/ground, RSET, default-off network and U2 control. A local In1.Cu ground extension provides returns. The original script's fixed driver vias collided with backside components; the revised router searches for clear escape sites. Staggered connector vias avoid the existing LCD_DC route. Host enable is routed before nearby gate/ground traces to retain access to R56.1.

Of 3,744 original copper items, 3,717 remain geometrically unchanged. The manifest identifies the 27 deliberately reworked local +5V_RF and TOUCH_IRQ items. All retained component placements are unchanged. The finished board adds 466 copper items, a net increase of 439. One unused new escape item was pruned under DRC control, followed by another continuity check. Route descriptions are construction history; the final board and continuity reports are authoritative.

Signal escapes include 0.15 mm traces and 0.5/0.3 mm vias. Connectivity does not establish current capacity, voltage drop, thermal resistance or stackup suitability.

## Validation

- 9 backlight net groups / 26 listed endpoints pass physical continuity.
- 7 backlight tests pass, including intentionally broken enable/channel copper, altered wiring and incorrect driver/current-setting parts.
- Existing display routing still passes all 25 groups. Another 16 display-routing, display-power and system-power regression tests pass.
- 248 components; 2,300/2,300 integrity checks; no placement or schematic/PCB parity failures.
- ERC remains at 30 findings. DRC retains only the four inherited USB1 hole-clearance findings.
- Unconnected items decrease from 340 to 327. Whole-board routing remains incomplete.
- The full board-check script passes. The manufacturing gate remains blocked by the documented engineering and native-check findings.
- Before-install checkpoint: `archive/handset-before-backlight/e2ab80e85e99/`.

Reproduce the staged work, starting with the archived pre-update generated directory, using `prepare_handset_backlight.py`, `route_handset_backlight.py`, and `finish_handset_backlight_routing.py`. Preparation intentionally refuses to overwrite an already installed update. Validate the installed board with `check_handset_pcb.sh` and `test_handset_backlight.py`.

Next: qualify the routed display/backlight power and startup behavior, confirm the purchased panel/touch configuration, and complete expansion power enable/fault handling. This update does not authorize fabrication or power-up.
