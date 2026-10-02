# U20 local modem converter layout — 2026-09-26

**INCOMPLETE — NOT FOR FABRICATION OR POWER.** U20's local conversion circuit and switch-controlled enable network are routed. External battery and modem power distribution, current capability and startup qualification remain open.

## Installed layout

Retain TPS63070RNMR, the 1.5 µH L4, two 10 µF input capacitors, three 22 µF output capacitors, VAUX bypass and existing divider/enable values. Rotate L4 to align its terminals with the two switch nodes. Move C52/C53/C54 to (99/102/105, 49.5), angle 270°. Move R60 to (95.4,48.6), angle 180°, and R61 to (93.7,49.7). Other footprints and all 1,971 previous track/via items are preserved.

- Route both switch nodes on F.Cu, using 0.25 mm escapes and 0.6 mm wider sections toward L4.
- Connect both VIN pin numbers, including the split pad 12 shapes, to C50/C51. Connect both VOUT pin numbers, including split pad 7, to the three output capacitors; use 0.3 mm QFN escapes and a 0.8 mm capacitor-bank connection.
- Route a separate output-capacitor sense branch to R60 and the FB network to U20.5. Route VAUX only to its bypass capacitor.
- Route the existing R62/R63/Q3/Q4/R64 enable network and connect Q4's SYS_EN input to SW19.2. This completes the physical control path; it does not qualify switching behavior.
- Add local F.Cu/In1.Cu ground planes, two 0.6/0.3 mm power-ground vias and twelve 0.8/0.4 mm local return vias. U20.4 connects through the filled local plane. Grounded PS/SYNC selects forced PWM; VSEL is grounded. PG and unused FB2 remain intentionally unconnected.

Added copper: 173 track/via items and two zones. No schematic or component-value changes. The source hashes, moved references, control route lengths and return-via positions are in [modem-routing.json](generated/modem-routing.json).

## Startup and power limits

R60/R61 set a nominal **3.792 V** output using the 0.8 V feedback reference. This is not measured output accuracy; resistor/reference errors, ripple, load transients and distribution loss remain to be evaluated for the chosen modem.

R62/R63 are 390 kΩ/100 kΩ. With Q3 released, the nominal 0.8 V rising EN threshold corresponds to **3.92 V at VBAT**; the typical 0.7 V falling threshold corresponds to **3.43 V**. Thus a nominal 3.7 V pack may not start the modem from off even though an already running converter can remain enabled. These are typical divider calculations, not guaranteed thresholds. Review the intended behavior and tolerances against the battery discharge curve and modem burst demand before finalizing the divider. Values were retained rather than changing the power policy during routing.

The MakerFocus pack/current-demand mismatch remains unresolved. The IC switch-current figure is not a qualified modem output-current rating. Review the narrow QFN/PGND escapes, via current and temperature, complete return loops, L4 saturation/RMS limits, capacitor effective capacitance and ESR, thermal margin and battery wiring under worst-case burst load. Do not infer a 2 A board capability from continuity or the device headline rating.

[TI TPS63070 datasheet](https://www.ti.com/lit/ds/symlink/tps63070.pdf) supplies the pin mapping, nominal feedback/enable thresholds and layout requirements used for this check.

## Verification

- [Continuity](generated/modem-continuity.json): all **48 physical pads** pass, covering the local battery net, both switch nodes, output, feedback, VAUX, enable/disable, SYS_EN and ground. Duplicate pad shapes for U20.7 and U20.12 are included individually.
- [Negative test](generated/modem-negative-tests.json): removing MODEM_L1 copper from a temporary copy correctly fails continuity with unchanged net labels.
- Native DRC retains four existing USB1 hole-clearance findings, with no new findings. Unconnected items **426 → 393**. Zero schematic parity findings. Native ERC remains 30 findings.
- 2,104 artifact-integrity assertions pass. The full board check runs the existing power/regulator/supervisor checks and regenerates PDF/SVG previews.
- No hardware was fabricated, powered or measured. Circuit/footprint review and analog layout qualification remain required.

## Reproduction and next work

`scripts/route_handset_modem.py` stages a one-shot update and checks preservation. The original checkpoint is archived under `archive/handset-before-modem-routing/dacd82fa6423/`. `scripts/check_handset_modem.py` is included in `scripts/check_handset_pcb.sh`.

Next: resolve modem startup/current requirements and route its external battery and load feeds accordingly. Display-branch requirements, the unused 1.8 V rail and other README blockers also remain open.
