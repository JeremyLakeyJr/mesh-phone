# U7 input, switch and ESP32 distribution — 2026-09-26

**INCOMPLETE — NOT FOR FABRICATION OR POWER.** This completes a bounded part of the README's Power supplies checklist. Peripheral supply distribution, other regulators and hardware qualification remain open.

## Installed copper

- Charger VSYS at C6.1 feeds U7 input capacitor C20.1 through a 0.8 mm trunk, with 0.4 mm pad escapes. The existing local C20-to-U7 circuit is preserved.
- U7 output capacitor C21.1 feeds ESP32 bulk capacitor C2.1 through a 0.8 mm trunk; C2.1 feeds U1.2 with 0.6 mm copper and C3.1 with 0.25 mm copper.
- SW19.1 receives VSYS; SW19.2 reaches U7 EN and R30.1; SW19.3 reaches ground. This switch controls enable, rather than carrying the main load current.
- An In1.Cu ground zone under the ESP32 shield and bypass capacitors connects all thirteen U1.41 exposed-ground pads. Local vias connect U1.1/U1.40 and C1/C2/C3 ground pads. The zone has priority 1 where it overlaps the existing same-net power-entry ground zone.
- New layer-transition/ground vias use 0.8 mm diameter and 0.4 mm drill. Existing module via-in-pad geometry remains subject to fabrication-process review.
- Routing excludes the ESP32 antenna rule area and the trackball opening. All footprint positions and all 1,424 prior track/via items are preserved; 214 track/via items and one ground zone are added.

The main input trunk is 69.261 mm; the output trunk is 81.173 mm plus a 25.680 mm branch to U1.2. Exact escape lengths, widths, via positions and layer-transition counts are recorded in [main-distribution.json](generated/main-distribution.json). These are long supply routes and require stackup/load review before release. As an illustrative trace-only calculation at 20 °C with **assumed** 35 µm copper, R = 1.724e-5 × length / (width × 0.035): the new input route including escapes is approximately 50 mΩ, and output route through U1.2 approximately 73 mΩ. At 1 A those imply approximately 50 mV and 73 mV drop respectively. This excludes vias, existing local copper, return paths, copper tolerance and heating; it is neither a current rating nor proof of acceptable transient response. The battery/modem current-budget blocker remains open.

## Verification

- [Physical continuity](generated/main-distribution-check.json): 38 pads pass in VSYS, SYS_EN, +3V3 and GND groups, including every U1.41 ground pad.
- [Negative test](generated/main-distribution-negative-tests.json): removing SYS_EN copper from a temporary board is correctly rejected despite unchanged net assignments.
- Existing U7 26-pad, power-entry 118-pad, supervisor 67-endpoint and charge-inhibit checks pass.
- 2,104 artifact-integrity checks pass; 238 components; zero schematic parity findings.
- Native DRC: four existing USB1 hole-clearance findings, **no new findings**. Unconnected items decrease **483 → 470**. Native ERC remains 30 findings.
- No physical board was fabricated, powered or measured.

## Remaining work

Complete U7 peripheral distribution and U10/U11/U20 regulator layouts; qualify supply/return paths, current, voltage drop, startup, thermal margin and transient response against the actual stackup and loads. Finish ESP32 reset/boot and other signal wiring. Resolve passive MPN/DC-bias qualification, battery limits, USB clearance findings and all other README/release blockers. Reconcile SW19 with the enclosure opening. Supervisor commissioning firmware still inhibits charging; durable fault handling and permission/rearm remain unfinished.

## Sources and reproducibility

Pin and layout references: [TI TPS63802 datasheet](https://www.ti.com/lit/ds/symlink/tps63802.pdf), [Espressif ESP32-S3-WROOM-1/1U datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf).

`scripts/route_handset_main_distribution.py` stages a one-shot update from the pre-step source board and asserts footprint/copper preservation. Source hashes are recorded in its JSON report; the pre-step checkpoint is archived under `archive/handset-before-main-distribution/947efb32e5ff/`. `scripts/check_handset_pcb.sh` now runs the physical continuity check on the installed board whenever the routing marker exists. Passing artifact checks does not release the design for fabrication.
