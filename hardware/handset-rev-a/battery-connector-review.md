# Battery connector implementation — 2026-09-27

J1 is now **Molex 2053380002**, replacing the previous JST PH connector in both `generated/power.kicad_sch` and `generated/handset.kicad_pcb`. The connectivity specification, placement table, exported netlist and previews are synchronized. This implements the higher-current battery direction; it does not qualify the complete battery path.

[Molex specifies](https://www.molex.com/en-us/products/part-detail/2053380002) a 2.6 mm mated height, positive lock and maximum 6.5 A/contact. These are component ratings, not a verified system current rating. The installed standard KiCad footprint references Molex drawing `2053380002_sd.pdf`; direct retrieval of that drawing failed during this review, so independent land-pattern/drawing signoff remains open.

## Placement and connections

- Back side, origin **127.4 × 106.0 mm**, angle **180°**. The connector opens toward increasing board Y; check the mating plug, wire bend and strain relief against the actual assembly.
- Pin **1 = BAT_PACK_POS**, pin **2 = GND**. Do not infer assembled harness polarity from wire colors or the mating-side view.
- Replaced only the two old J1 trace stubs with six 0.6 mm B.Cu segments. No vias added. All 2142 other track/via items and every other footprint are preserved. This retains the existing trace width; thermal/current qualification of the complete path remains open.
- The first aligned-pad placement collided with the U11 area; the installed orientation and location avoid those overlaps. Native DRC reports no new clearance, courtyard or solder-mask findings.
- F2 remains `046701.5NRHF / 1.5A`. It remains a blocker for the proposed handset/modem load; the connector change does not authorize applying power.

## Harness and fuse evidence

[Molex 2196572020](https://www.molex.com/en-us/products/part-detail/2196572020) is a candidate two-circuit, 50 mm, 20 AWG Pico-Lock pigtail. Confirm the mating drawing, pin numbering, complete pack-lead joint and strain relief before freezing the harness. The candidate pack has a separate NTC lead; J1 remains power-only and does not replace the existing thermistor connection.

The [Littelfuse 467-series datasheet](https://www.littelfuse.com/assetdocs/fuse-467-datasheet?assetguid=4a59f034-1cca-460e-a5ba-e1e66247c76d), page 2, specifies a 25% continuous-operation derating and gives a 0.80 temperature factor at 70°C. A 5 A `0467005.NRHF` therefore screens at 3.75 A at nominal temperature and **3.0 A at 70°C**. The latter is below the initial 3.302 A battery-current scenario. This is a hot-board screening condition, not an assertion that the pack may operate at 70°C. The part is not installed: full ambient, inrush, trip-time, PCM and wiring coordination are still required. Do not simply increase the fuse rating until a spreadsheet passes.

## Verification and checkpoint

- 118 local power-entry pads pass physical continuity checks.
- Removing BAT_PACK_POS copper while retaining its net labels causes the continuity check to fail. Evidence: `generated/battery-connector-negative-test.json`.
- Native schematic parity: zero findings. DRC: four inherited USB1 hole-clearance findings; 393 unconnected items remain.
- Geometry preservation is enforced by `scripts/prepare_handset_battery_connector.py`; source hashes guard installation.
- Previous design checkpoint: `archive/handset-before-battery-connector/1555274475f1/`.

Next: coordinate F2 and the battery copper/returns for the actual load and thermal envelope, then route U20's external feed. Pack dimensions, mating harness, NTC and physical enclosure fit remain unqualified. **DO NOT FABRICATE OR POWER.**
