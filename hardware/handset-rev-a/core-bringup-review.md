# Boot/reset and control-chip routing checkpoint

2026-10-07. **Engineering checkpoint; not released for fabrication or power-up.**

Follow-up: the matrix connections are completed in the
[keypad routing checkpoint](keypad-routing-review.md); target firmware and bench
qualification remain open.

The ESP32 boot pull-up and both service buttons now have copper connections.
U2 (TCA8418) has 3.3 V, exposed-pad/pin ground, shared MCU reset, SDA, SCL and
an interrupt connection to the ESP32. R5 supplies the interrupt pull-up.
The existing 10 kΩ EN pull-up and 1 µF reset capacitor are retained.
This enables the next control-firmware work; it does not demonstrate working
USB programming, display operation or keypad scanning on hardware.

## Layout changes

- R2 moves from (98, 62) to (98.8, 63.3) mm on the back to provide routing access.
- C4 moves from (128, 119) mm on the front to (123.5, 117.6) mm on the back,
  beside U2's supply fanout. No component or schematic net is changed.
- All duplicate physical button contacts are connected explicitly. Ground
  returns use through vias outside the component pads and lower-board pours.
- The crowded U2 pins use explicit fanout and ordinary 0.5 mm / 0.3 mm drilled
  through vias. No via-in-pad processing is introduced.
- One existing KEY_COL3 segment is split and locally rerouted around the new
  vias. Its lower trunk and branch connections are retained. All other existing
  tracks/vias retain their UUID, geometry and net assignments.
- Routing uses outer and inner signal segments. The USB reference region is
  excluded from new inner routing; the independent USB reference checks remain
  required. The added lower-board ground fills do not establish full-board
  return-path qualification.

`generated/core-routing.json` records the source/final hashes, moved parts,
rerouted segment and incremental route lengths. Route lengths are router
segments, not complete electrical path measurements; manual fanout is additional.

## Checks

`check_handset_core.py` reads actual PCB connectivity, including every duplicate
physical switch pad. It verifies the seven bring-up net groups, pull-up/bypass
values and local bypass placement. `test_handset_core.py` exercises eight cases:
installed routing, open boot pull-up, individual boot/reset contact opens,
controller supply/reset opens, wrong pull-up value and swapped bus assignments.
Both run in the main PCB check script. The manufacturing release gate checks
core connectivity independently of the saved routing manifest.

The original connected-pad groups are compared with the staged board before
installation; none may lose a connection. Existing display, backlight,
expansion, USB and power checks also remain required. Native DRC and schematic
parity must be zero under the unchanged project rules.

Saved checkpoint results: 2,537/2,537 integrity assertions; zero native DRC
violations and zero parity findings; eight core regression cases pass. All 642
previous connected-pad groups are preserved. Unconnected items drop from 279
to 258. The existing 30 ERC findings and 11 engineering blocker groups remain.

## Remaining bring-up work

The bottom-edge buttons create long boot/reset nets. Qualify noise/ESD immunity,
reset timing, supply rise/fall behavior and recovery from repeated power cycles
before release. The RC values alone do not establish reliable reset under a
slow or unstable supply. The [Espressif schematic checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)
is the reference for EN and boot-strapping review.

U2's active-low RESET and open-drain interrupt wiring follow the
[TI TCA8418 datasheet](https://www.ti.com/lit/ds/symlink/tca8418.pdf).
The keypad matrix still needs completion. Firmware must probe U2, configure its
GPIO/keypad functions, establish safe display/backlight defaults and service
interrupts. Do not enable the backlight before the panel/power sequence has been
qualified. Bus timing and signal integrity are not verified by CAD continuity.

After the overall hardware is approved for controlled commissioning, verify
rails and reset first, then test manual ROM-download entry using BOOT and RESET,
USB enumeration, programming, U2 communications and individual control outputs.
This is a future bench sequence, not permission to power the current incomplete
board. All open release blockers in `release-blockers.json` remain applicable.
