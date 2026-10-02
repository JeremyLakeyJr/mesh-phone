# U10 feed and LF RFID supply distribution — 2026-09-26

**INCOMPLETE — NOT FOR FABRICATION OR POWER.** The U10 input and LF RFID supply/ground branch are routed. This does not complete the display branch, LF signal/coil circuits, or hardware qualification.

## Installed copper

- Connect the existing VSYS network at C20.1 to U10 input capacitor C25.1. The new trunk is 0.8 mm wide and 64.645 mm long, with 0.4 mm pad escapes of 1.0 and 0.95 mm. It uses layer transitions and does not use the thin switch-enable wiring as a load path.
- Connect C26.1 to C24.1/U9.3 and C45.1/U18.14. The two 0.5 mm branches are 14.869 and 13.969 mm. The U9 supply segment is 0.3 mm, 7.520 mm; the U18 supply segment is 0.25 mm, 2.754 mm. Existing U18 high-level control connections at pins 10 and 13 are also routed.
- Connect C24/C45 returns, U9 ground pins and U18 ground/control pins with local B.Cu/In1.Cu zones, short tails and nine 0.8 mm diameter/0.4 mm drill vias. The local planes join existing system ground.
- Preserve every footprint and all 1,834 previous track/via items. Add 137 track/via items and two zones. No schematic or value changes.

Exact route lengths, escapes and via positions are recorded in [reg5-distribution.json](generated/reg5-distribution.json). At assumed 35 µm copper and 20 °C, the new VSYS trunk plus escapes contributes roughly 42 mΩ before vias, existing source copper, returns, copper tolerances and heating. The upstream VSYS feed now supplies both U7 and U10; qualify their combined current and voltage drop. This estimate is not a current rating.

## Voltage and layout qualification

The previously calculated static regulator range, 4.782–5.208 V, lies within the 4.5–5.5 V supply ranges specified for [NXP HTRC110](https://www.nxp.com/docs/en/data-sheet/037031.pdf) and [TI SN74AHCT125](https://www.ti.com/lit/ds/symlink/sn74ahct125.pdf). This leaves approximately 0.28 V at the lower boundary before wiring drop, ripple and transient effects. It does not establish loaded compatibility or qualify the coil drive.

Review local bypass placement and return impedance, particularly the 7.52 mm C24-to-U9 supply segment, before final layout release. Qualify coil current, rail transients, resistor/capacitor MPNs, regulator and battery current budgets, startup and thermal margin. No bench measurements are available.

The display connector J26.1 and capacitor C49.1 remain outside this connected branch. Confirm the exact panel's voltage/current and connector assignment before completing that branch; do not treat LF-device voltage compatibility as display approval.

## Verification

- [Physical checks](generated/reg5-distribution-check.json): all 36 pads pass, including upstream U3/C20, U10 local conversion/enable and LF supply/ground endpoints.
- [Negative test](generated/reg5-distribution-negative-tests.json): removing only the new VSYS feed from a temporary copy correctly fails continuity despite unchanged net labels.
- Native DRC retains four existing USB1 hole-clearance findings, with no new findings. Unconnected items **446 → 426**. Zero schematic parity findings; native ERC remains 30 findings.
- 2,104 integrity assertions pass. The full board check runs existing power, supervisor, inhibit and regulator checks and refreshes schematic/board previews.
- No functional LF communication, display operation or loaded supply behavior is claimed. Signal/clock/coil routing and validation remain open.

## Reproduction

`scripts/route_handset_reg5_distribution.py` stages a one-shot update and asserts preservation. Source hashes and geometry evidence are in its JSON report. The source checkpoint is archived at `archive/handset-before-reg5-distribution/4d7101762a59/`. `scripts/check_handset_reg5_distribution.py` is included in `scripts/check_handset_pcb.sh`.

Next regulator layout: U20. Also resolve display-branch requirements, the unused 1.8 V rail, and the other README fabrication blockers.
