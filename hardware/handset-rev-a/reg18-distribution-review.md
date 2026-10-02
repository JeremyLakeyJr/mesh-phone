# U11 input feed and output refinement — 2026-09-26

**INCOMPLETE — NOT FOR FABRICATION OR POWER.** The U11 input feed is now routed, and its local output connections have been shortened. The rail has no assigned external load in the current schematic; that is an unresolved design decision, not completed load distribution.

## Installed change

- Connect U7 output at C21.1 to U11 input capacitor C27.1 using 0.5 mm copper, 39.051 mm long, with two layer transitions. U11 VIN/EN now connect physically to U7 output.
- Move C28 to (119, 100), angle 180°, without moving other footprints. Add a 0.4 mm ground tail and a 0.6 mm diameter/0.3 mm drill ground via at (116.8, 100). Refill the existing planes.
- Replace only the 56 previous +1V8 track/via items. Preserve the other 1,660 copper items, including the local SW connection and input bypass. Add 108 track/via items in total.
- Shorten the output path from 16.046 to 15.003 mm (0.5 mm, B.Cu). Shorten the sense path from 14.184 to 12.983 mm (0.2 mm, two layer transitions). These remain relatively long, constrained routes; the refinement does not close analog layout qualification. Revisit the cell layout after resolving the rail's purpose.

The input trace alone is approximately 38.5 mΩ assuming 35 µm copper at 20 °C, before vias, existing local necks, return path, tolerance and heating. This is a screening estimate, not a current rating. No load capability is claimed.

## Rail inventory finding

Both the schematic connectivity specification and PCB assign +1V8 only to **U11.8, L3.2 and C28.1**. There is no external device or connector on that net. The check records this explicitly and rejects a changed endpoint inventory so that a future load addition must be reviewed and routed. Do not attach an arbitrary module to make the rail appear complete. Resolve whether a selected interface needs 1.8 V; otherwise remove or depopulate this unused converter through a consistent schematic/BOM/PCB update. Existing functional connections are retained in this step.

## Verification

- [Distribution check](generated/reg18-distribution-check.json): 17 physical pads pass, including the U7 source, U11 local circuit and C28 ground return.
- [Negative test](generated/reg18-distribution-negative-tests.json): removing only the newly added +3V3 feed from a temporary board correctly fails the U7-to-U11 continuity check.
- Native DRC: four existing USB1 hole-clearance findings, no new findings. Unconnected items: **459 → 458**. Zero schematic parity findings; native ERC remains 30 findings.
- 2,104 artifact-integrity checks pass. The full board check runs existing regulator, power-entry, supervisor, charge-inhibit and main-distribution checks and regenerates PDF/SVG previews.
- No hardware was built or powered. Current, thermal, noise, transient response and startup behavior remain unqualified.

## Reproduction and remaining work

`scripts/route_handset_reg18_distribution.py` stages this one-shot update, asserts preservation of unrelated copper and footprints, and records hashes/geometry changes in [reg18-distribution.json](generated/reg18-distribution.json). The source checkpoint is archived at `archive/handset-before-reg18-distribution/0c8f2e9137d7/`. `scripts/check_handset_reg18_distribution.py` is included in the full board check script.

Resolve the unloaded rail, finish U10/U20 local layouts and remaining peripheral distribution, qualify the final capacitor/inductor MPNs and supply budget, and clear the other README release blockers. [TI's TPS62840 datasheet](https://www.ti.com/lit/ds/symlink/tps62840.pdf) requires close input bypass and a quiet output-capacitor sense connection; continuity and DRC alone do not establish those performance requirements.
