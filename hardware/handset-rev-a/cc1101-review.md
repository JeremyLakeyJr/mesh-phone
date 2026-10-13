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

## Support copper checkpoint — 2026-10-11

Crystal, DCOUPL, bias and filtered supply routing is installed. Six rear-layer
bypass branches each connect one supply pin to its own capacitor and feed via;
front-layer distribution joins them through L11. Every support capacitor has a
local ground return. The oscillator routes stay on B.Cu without signal vias:
X1 totals 8.6407 mm and X2 6.8364 mm including load-capacitor branches. All 528
sampled points across their adjacent In2.Cu return corridors have filled ground.
These are geometric checks; oscillator startup and frequency are unqualified.

U5 uses the local `Handset:CC1101_RGP20_MaskedThermalVias` footprint. Numbered
copper lands retain the original geometry. Its 2.7 mm square exposed pad now
has four 1 mm square mask openings and four 1 mm square paste openings
(54.9% coverage). Five 0.5/0.3 mm thermal vias occupy the masked cross between
those windows, with 0.15 mm nominal drill-to-opening margin. Both faces are
tented. Native Gerber export confirms the 1 mm mask apertures; KiCad does not
apply local copper-pad mask expansion to these non-copper aperture pads.
This explicitly masks the holes instead of relying on via tenting
inside an otherwise open exposed-pad mask aperture. Fabricator registration
and tenting capability, assembler paste/reflow approval and thermal-joint
inspection remain release requirements.

The arrangement follows the separate supply/ground return and thermal-via
guidance in [TI SWRS061I, section 7.8](https://www.ti.com/lit/ds/symlink/cc1101.pdf).
It is a custom four-layer adaptation, not a qualified reproduction of the TI
reference board. The selected [Abracon ABM8](https://abracon.com/Resonators/abm8.pdf)
and 15 pF load capacitors are unchanged; actual parasitic loading and crystal
drive still require measurement.

The guarded installation preserved all 9,587 previous copper items and 594
previously connected pad groups, adding 93 copper items. Eighteen unrouted
support/RF footprints were repositioned; R12 and the matching network still
need routing. The source archive and hashes are recorded in
[cc1101-support-routing.json](generated/cc1101-support-routing.json).
The support checker passes 47 checks and 22 regression cases, including broken
connections, merged bypass branches, wrong oscillator layer, absent ground
reference and exposed thermal holes. Native DRC and schematic parity are clear;
180 open connections and 20 ERC findings remain across the board. Manufacturing
release stays blocked. Next: refine and route the CC1101 balanced RF network
and antenna connection, followed by its digital interface and remaining loads.

## RF copper checkpoint — 2026-10-11

The complete CC1101 balun, matching/filter network and J21 antenna path now
have checked copper continuity. Twelve previously unrouted footprints were
repositioned, including J21 at (130.5, 44.7) mm. All RF signal copper remains
on B.Cu with no signal vias. The IC-to-inductor branches measure 2.1353 and
2.1768 mm (0.0415 mm difference); the antenna feed totals 2.5092 mm. Internal
matching tracks are 0.2 mm wide and the antenna feed is a 0.34 mm screening
target. These dimensions do not certify a 50-ohm feed or matched RF ports.

In1.Cu and In2.Cu ground extend beneath the network. Component-side ground
uses 0.5 mm zone clearance with local grounded returns at C65, C66, C68 and
both J21 ground pads. Nine added 0.5/0.3 mm ground vias are tented on both
faces. All 1,014 sampled points along the RF tracks and their side margins
have adjacent filled In2.Cu ground. The circuit values remain the previously
reviewed 868/915 MHz network. [TI SWRS061I, Figure 11 and section 7.8](https://www.ti.com/lit/ds/symlink/cc1101.pdf)
remain the circuit/layout references; this custom four-layer arrangement
requires impedance review and conducted measurements before release.

The guarded installation preserved all 9,680 previous copper items and 558
connected pad groups. The archive, placements and board hashes are recorded
in [cc1101-rf-routing.json](generated/cc1101-rf-routing.json). Live RF checks
cover every matching node, all connector grounds, layer/width/length limits
and adjacent reference copper. All 44 checks and 32 regression cases pass.
The previous clock, bypass and thermal-via checks remain enabled. Native DRC
and schematic parity have zero findings; 159 open connections and 20 ERC
findings remain board-wide. Manufacturing release stays blocked.

Next, route the CC1101 digital interface and its pull-up/test point, then
continue the remaining peripheral routing. Before RF release, validate the
actual stackup and copper geometry, connector/case placement, antenna match,
conducted power, receive sensitivity, harmonics/spurs and coexistence. Determine
from measurements whether the optional 699 MHz spur filter is necessary.

## Digital interface checkpoint — 2026-10-12

CC1101 SCK, MOSI and MISO now connect to the established host SPI bus. CS
connects to U1.24 and the 10 kOhm R12 pull-up; R12 also connects to +3V3.
GDO0 connects to U1.25 and GDO2 reaches TP1. The added digital traces are
0.15 mm wide. All 31 new through vias use 0.5 mm lands, 0.3 mm drills and
tenting on both faces. The final GDO2 branch contains 14.3255 mm of added
copper and avoids J20's connector keepout.

C12 moves 0.5 mm left to make room for separate signal escapes. Its independent
supply branch and local ground return are rebuilt, and C11's ground via moves
to (116.5, 38.3) mm. Two existing I2C tracks are reworked at the host escape.
All six independent rear bypass branches, DCOUPL, oscillator and thermal-via
checks still pass. No circuit values, board rules or stackup settings change.
The installer preserves all 537 previously connected pad groups and all
9,721 unreplaced source copper items. Eight old copper items are replaced;
789 new items are added. Source archive, hashes and changed placement are in
[cc1101-digital-routing.json](generated/cc1101-digital-routing.json).

The inner-layer digital fanout passes beside the radio and toward the host,
including the still-unrouted GNSS region. RF and clock reference corridors are
protected during routing and checked again after plane fill; the CC1101 and
SX1262 RF/clock checks and the USB reference checks pass. This is continuity
and geometry evidence, not a complete return-current or signal-integrity
qualification. Review the final plane geometry after the remaining devices
are routed. Qualify shared-bus loading, edge rates, clock frequency, MISO
release, CS timing and power/reset behavior on assembled hardware. Firmware
GDO configuration, register access and RF operation remain unverified.

The digital checker passes 13 checks and 15 regression cases, including each
radio interface endpoint, both pull-up pads, wrong pull-up value, trace width
and via tenting. Native DRC and schematic parity have zero findings; opens
fall from 159 to 151. The board still has 20 ERC findings and remains blocked
from manufacturing release. Next: complete the SX1262 digital interface and
continue the remaining peripheral routing, then finish the overall return
planes, mechanical/BOM review and fabrication checks.
