# U10 local 5 V boost layout — 2026-09-26

**INCOMPLETE — NOT FOR FABRICATION OR POWER.** Local U10 conversion, feedback, ground and switch-enable copper is installed. External VSYS feed and +5V_RF load distribution remain open.

The subsequent [distribution update](reg5-distribution-review.md) completes the VSYS feed and LF power/ground branch. This document records the preceding local-layout checkpoint.

## Change

Retain TPS61023DRLR, L2 XFL4020-102MEC (1 µH), C25 10 µF, C26 22 µF, R34 732 kΩ and R35 100 kΩ. Move C26 to (74.5,123), angle 180°, R34 to (69.6,121.4), and R35 to (71.8,121.4). These positions avoid the inductor courtyard and existing keypad copper. Other footprints and all 1,768 existing track/via items are preserved.

The SW path stays on B.Cu, about 3.10 mm long, with a 0.3 mm IC escape widening to 0.6 mm. VOUT uses a 0.3 mm escape and 0.6 mm connection to C26. VIN-to-L2 uses 0.6 mm B.Cu copper, 10.173 mm long; the input bypass-to-VIN branch is 0.35 mm. Feedback routes on B.Cu with a separate 0.2 mm sense branch from C26 to R34 and 0.15 mm FB routing. SW19's SYS_EN reaches U10.2 through a 0.15 mm control trace, 26.646 mm with one layer transition; it does not carry load current.

Three 0.6 mm diameter/0.3 mm drill ground vias and local B.Cu/In1.Cu planes connect the converter and capacitor returns to system ground. The inner ground zone joins the existing supervisor ground region. 66 track/via items and two zones are added. No schematic or component-value changes were made.

## Divider screening and limits

Using the existing 732 kΩ/100 kΩ, 1% divider and the TPS61023 nominal 0.6 V reference gives **4.992 V**. Combining the resistor extremes with the reference's ±2.5% accuracy gives approximately **4.782–5.208 V**, before ripple, dynamic regulation, resistor temperature coefficient and other errors. This is a calculated corner range, not a measured output or guarantee. Validate every downstream load's permitted voltage and refine the divider/part selection if necessary.

The converter's switch-current specification is not an available handset output-current rating. Still qualify L2 saturation/RMS current, capacitor effective capacitance and voltage ratings, input source/battery limits, switching loss, copper temperature, startup, output ripple and transient response. Review the local loop geometry and return impedance against the selected stackup; native DRC does not prove analog performance. Keep the whole power-supplies checklist open.

## Verification

- [Continuity](generated/reg5-continuity.json): all 19 physical pads pass in VSYS, SW, output, FB, SYS_EN and ground groups, including U7 system-ground/enable references.
- [Negative test](generated/reg5-negative-tests.json): removing FB copper from a temporary board correctly fails the checker with unchanged net labels.
- Native DRC: four existing USB1 hole-clearance findings, no new findings; unconnected items **458 → 446**. Zero schematic parity findings; native ERC remains 30 findings.
- 2,104 integrity assertions pass. Full board checks cover existing regulators, power entry, supervisor, charge inhibit and power distribution and regenerate PDF/SVG previews.
- No hardware was built, powered or measured.

## Sources and reproduction

[TI TPS61023 datasheet](https://www.ti.com/lit/ds/symlink/tps61023.pdf): pin functions, reference accuracy and layout requirements. Orderable passives and the final assembled load budget still require qualification.

`scripts/route_handset_reg5.py` stages a one-shot update and checks preservation before saving. [reg5-routing.json](generated/reg5-routing.json) records source hashes, moves and routing metrics. The original checkpoint is archived at `archive/handset-before-reg5-routing/98ec0e1db98e/`. `scripts/check_handset_reg5.py` is included in `scripts/check_handset_pcb.sh`.

Next: connect U10 supply/load distribution and complete U20 local layout. The unused 1.8 V rail and other README release blockers remain unresolved.
