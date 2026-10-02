# U11 local 1.8 V layout — 2026-09-26

**INCOMPLETE — NOT FOR FABRICATION OR POWER.** This completes local copper for the U11 regulator under the README Power supplies checklist. It does not complete rail distribution or qualify this converter under load.

Superseded routing details: see [U11 distribution refinement](reg18-distribution-review.md) for the current C28 position, shorter paths and completed input feed. This document records the preceding local-layout checkpoint.

## Changes

U11 remains TPS62840DLCR. L3 (XFL4020-222MEC, 2.2 µH) is rotated so its switch pad faces U11.7. C27 (4.7 µF) moves to (120.8, 97.4), angle 270°, closer to VIN/GND. C28 (10 µF) retains its existing position; placing it below L3 conflicts with the battery connector. All other footprints and all 1,638 existing track/via items are preserved.

The SW connection is about 2.5 mm long on B.Cu, with a 0.25 mm IC escape widening to 0.5 mm. Input bypass and EN routing stay on B.Cu. The L3-to-C28 output connection is 0.5 mm wide, 16.046 mm long and on B.Cu. The 0.2 mm VOS-to-C28 path is 14.184 mm with two layer transitions. These latter routes are constrained by the battery connector and existing copper: **review shortening/relocating the output capacitor and sense path before release**. Continuity is not proof of a low-noise sense connection or acceptable transient behavior.

Local B.Cu and In1.Cu ground zones and four 0.6/0.3 mm ground vias connect the converter return to existing system ground. MODE, VSET and STOP are grounded, EN follows VIN. No schematic or component-value changes were made. Added copper totals 78 track/via items and two zones. Front copper is excluded from the new output routes because of the microSD socket's routing restriction.

## Evidence

- [Local continuity](generated/reg18-continuity.json): all 15 physical pads pass across input/enable, switch, output/sense and ground groups. Includes a system-ground reference at U7.8.
- [Negative test](generated/reg18-negative-tests.json): removing REG18_SW copper from a temporary board causes the continuity checker to reject it despite unchanged net labels.
- Native DRC retains only the four existing USB1 hole-clearance findings; no new overlap, short, clearance or keepout findings.
- Unconnected items decrease **470 → 459**. Zero schematic/PCB parity findings. ERC remains 30 findings; 2,104 integrity assertions pass.
- Existing power-entry, U7, supervisor, charge-inhibit and ESP32 power-distribution checks run through `scripts/check_handset_pcb.sh`. PDF and SVG previews are regenerated.
- No hardware was fabricated, powered or measured.

## Remaining qualification

Connect C27 to the main 3.3 V supply and distribute 1.8 V to its loads. Review the long output/sense routes and ground-return impedance. Freeze capacitor MPNs and verify effective capacitance under bias, L3 current/inductance limits, startup and transient response, load budget, thermal margin and sequencing. U10/U20 local layouts and the other README blockers remain open. Do not use the regulator's device rating as the assembled board's qualified current limit.

[TI TPS62840 datasheet, pin functions and layout guidance](https://www.ti.com/lit/ds/symlink/tps62840.pdf) supplies the pin-map and layout requirements used here. Nominal capacitor values alone do not satisfy its effective-capacitance requirements.

## Reproduction and preservation

`scripts/route_handset_reg18.py` stages the one-shot update and records source hashes, placement changes and route lengths in [reg18-routing.json](generated/reg18-routing.json). It refuses to rerun on an already updated source. The saved pre-step board is under `archive/handset-before-reg18-routing/cb532a4bc7c0/`. The physical checker is `scripts/check_handset_reg18.py`; it is included in the full board check script.
