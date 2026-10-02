# Display interface routing — 2026-09-28

**Implemented and installed:** display-interface routing passes physical continuity and introduces no new native DRC findings. Electrical qualification and whole-board release remain open.

## Scope

This pass connects U28–U31, their bypass capacitors and bias resistors, J26's dedicated LCD_3V0 supply/straps, translated SPI/control/touch signals, and their host connections. It also extends the existing +5V_RF distribution to the display branch and adds local ground returns. It retains the component selection documented in [the display interface review](display-interface-review.md).

Dense U29 and J26 pin escapes are laid out before longer branches. Longer host-control routes avoid the connector's front-layer escape area. Routing uses F.Cu, B.Cu and In2.Cu; In1.Cu remains the ground-reference layer. The existing antenna and trackball exclusions are respected. All 250 component placements and 2,142 pre-existing trace/via items are preserved. Original ground-zone boundaries are retained; a new In1.Cu ground extension connects the left-side return buffers and bypass capacitors to the existing plane. Ground pours are refilled around the additions. The microSD socket keepouts are respected.

This is physical routing, not an operating-current, timing or thermal qualification. The dense escapes include 0.15 mm traces. The long C26-to-C84 5 V feeder uses 0.4 mm traces (approximately 68.6 mm routed length); shorter display branches still require load/voltage-drop qualification. Via sizes must remain compatible with the chosen fabricator and assembly process; electrical load evidence must justify power-trace widths and voltage drop before release. No SPI clock rate or touch-bus capacitance is qualified by a connectivity test.

## Validation

`check_handset_display_routing.py` checks actual native KiCad copper connectivity from the supply/host anchors through the interface, including local and connector grounds. Its endpoint contract is independent of the routing manifest. Five regression tests pass: the installed board passes, while removing LCD_3V0 copper, breaking the panel clock, removing the new ground extension, or permanently enabling the MISO return is rejected. The ordinary board validation and manufacturing-release check also invoke this checker when the routing manifest is present.

- **25 net groups / 121 listed endpoint checks** pass physical continuity, including every connector ground pin.
- **2,298/2,298 artifact integrity checks** pass; zero schematic/PCB parity findings.
- Native ERC remains at **30** findings (24 isolated labels and six undriven power pins).
- Native DRC retains only **four inherited USB1 hole-clearance findings**. No new clearance, keepout or dangling-copper findings remain.
- Unconnected items decrease **433 → 340**. The rest of the PCB remains incomplete.
- Six display-power and five system-power regression tests pass. The full project validation script passes; the manufacturing release gate remains blocked.
- Nineteen unused escape-copper items were pruned after DRC, with continuity rechecked. The routing manifest is construction history; `display-routing-check.json` and native DRC describe final connectivity.
- Source-hash-guarded checkpoint: `archive/handset-before-display-routing/6ad53ae9b310/`.

## Still open

- Panel/CTP current limits and actual purchased option, FPC orientation and external cable.
- LDO heat, effective capacitor values, supply transients and startup/shutdown sequencing.
- SPI propagation delay, MISO turnaround/contention margin, I²C rise time/capacitance and host GPIO/reset behavior.
- Backlight current regulation/thermal qualification and remaining backlight control/return routing. This pass supplies the display branch; it does not complete every backlight connection.
- Expansion power enable/fault handling, full-board routing and all other release blockers.

**DO NOT FABRICATE OR POWER.**
