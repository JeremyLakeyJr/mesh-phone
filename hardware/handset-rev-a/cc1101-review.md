# CC1101 circuit completion — 24 September 2026

The CC1101 schematic now includes its clock, differential RF matching,
low-pass filter, antenna DC block and filtered/decoupled supply. This completes
the **schematic block**, not a working or qualified RF layout. All handset
release blockers remain active where applicable.

See [the schematic PDF, page 13](generated/handset-schematic.pdf),
[new component BOM](generated/cc1101-bom.csv) and
[circuit checks](generated/cc1101-checks.json).

## Implemented

- Y2 is Abracon ABM8-26.000MHZ-10-D-1-G-T: 26 MHz, 10 pF load,
  ±10 ppm initial tolerance, ±15 ppm temperature stability, -40 to +85 °C,
  50 Ω maximum ESR. C61/C62 are 15 pF C0G. Their estimated load is
  `15/2 + 2.5 = 10 pF`; actual parasitics and crystal drive require measurement.
  Initial, temperature and first-year aging sum to 27 ppm before loading error.
- Y2's custom footprint follows Abracon's recommended 1.30 × 1.05 mm pads,
  with 1.00 mm horizontal and 0.70 mm vertical gaps. Pins 1/3 are the crystal;
  pins 2/4 ground the case. Package chamfer is not a reliable pin-1 indicator.
- L5–L10 and C63–C68 implement TI's 868/915 MHz differential balun/matching
  and filter chain. J21 remains a separate 50 Ω antenna connector. The optional
  C126/L125 spur notch in TI's drawing is omitted; emissions testing must
  determine whether it is required. This network does not provide matched
  315/433 MHz operation.
- L11 filters the main 3.3 V feed into CC_VDD. C12 and C69–C73 provide a
  100 nF bypass for each supply-pin group; C74 adds local bulk capacitance.
  C11 stays on the dedicated DCOUPL output. That output is not joined to VDD.
- TP1 exposes optional GDO2 for debugging. The host-connected GDO0 and SPI
  interface remain. Firmware should set IOCFG2 to `0x2E` when GDO2 is unused,
  and configure SO for shared-SPI behavior; firmware is not implemented here.
- U5 pins 1/7/20 are now typed as inputs, SO pin 2 as tri-state, GDO2 pin 3
  as output, and DCOUPL pin 5 as a power output. Analog and bidirectional pins
  retain their appropriate types. No no-connect markers or waivers conceal
  missing RF branches.

The new BOM lists the 23 added schematic items (including the copper test pad)
and specified replacements for C11/C12. It is an addition list, not the full
handset purchasing BOM. Existing U5, R11, R12 and J21 remain in the main
connectivity/placement records.

## Verification and preservation

The project has 215 schematic components and 219 physical footprints including
mounting holes. All 1,942 schematic/PCB integrity assertions pass. There are
zero native parity findings and no new overlap, short, clearance or silkscreen
findings. The four pre-existing USB connector hole-clearance findings remain.

The independent CC1101 checker validates 90 topology/value conditions against
the native KiCad netlist. Five negative cases reject a shorted matching leg,
an incorrectly joined balun branch, a grounded crystal-terminal error, a
DCOUPL/VDD mix-up and the wrong crystal-load capacitor. Native ERC falls from
37 to 31 findings; the CC1101 sheet has no remaining findings.

All 792 previously routed copper items are preserved. Only the six existing
CC1101-area footprints U5, C11, C12, R11, R12 and J21 move. The other 190
existing footprints retain their placement and geometry. The previous project
is snapshotted before installation; exact source hashes, moved references and
snapshot path are recorded in [cc1101-update.json](generated/cc1101-update.json).

The existing 113-pad power-entry and 26-pad main-regulator continuity checks
still pass. No claim is made that the new CC1101 nets have copper continuity.
The board has 485 unconnected items, up from 445 because the added circuit is
not routed. Moving unrouted radio parts does not remove completed routing.

## Next work and release limits

RF component placement is provisional. It must be refined around short balanced
connections and continuous return planes, then routed against a chosen PCB
stackup with a controlled-impedance antenna feed. Do not use a general-purpose
autorouter to finalize the matching network. Verify crystal startup/frequency,
DC bias, supply noise, conducted RF power/sensitivity, harmonics/spurs and
antenna matching with the assembled case and other transmitters active.

SX1262 support circuitry, LF timing/analog circuitry and NFC antenna matching
remain unfinished. Charger firmware, complete board routing, modem adapter,
mechanical/antenna integration and independent release review also remain.
**Do not fabricate or power this incomplete handset.**

## Primary references

- [TI CC1101 SWRS061I](https://www.ti.com/lit/ds/symlink/cc1101.pdf): pin types,
  oscillator constraints, Figure 11 and Table 21.
- [TI SWRR045 reference-design archive](https://www.ti.com/lit/zip/swrr045):
  CC1101EM 868/915 MHz schematic/BOM/layout revision 3.0.0. The crystal/load
  selection here is explicitly different from that board's older NDK variant.
- [Abracon ABM8](https://abracon.com/Resonators/abm8.pdf): ordering options,
  electrical ratings and land pattern.
- [Murata inductor model/part list](https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/static-model/component-list-ind-s-2602.ashx?cvid=20260515010000000000&la=en-gb): LQW15AN wire-wound series.
- [Murata 1 pF C0G capacitor](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM1555C1H1R0CA01-01.pdf).
- [Murata 1.5 pF C0G capacitor](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM1555C1H1R5CA01-01A.pdf).
