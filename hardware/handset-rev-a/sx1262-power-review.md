# SX1262 core regulator support — 2026-09-24

**Engineering draft. Do not fabricate or power.** This step corrects the
core regulator circuit and initial component placement. It does not complete
or qualify the LoRa radio. No new copper has been routed.

## Implemented

- L12, **MLZ2012M150WT000**, 15 µH ±20%, connects U4.9 `SX_DCC_SW`
  to U4.7 `SX_VREG`. This is a shielded 2.0 × 1.25 × 1.25 mm part
  listed in Semtech's recommended-inductor table. KiCad's part-specific
  `L_TDK_MLZ2012_h1.25mm` footprint is used.
- C9 changes from the incorrect 100 nF to **470 nF ±10% X5R 10 V**,
  **GRM155R61A474KE15D**, between VREG and ground (Semtech C17).
- C8 receives an exact **GRM155R71C104KA88D** specification and moves
  closer to VBAT, pin 10. C75 and C76 use the same 100 nF ±10% X7R 16 V
  capacitor for local VDD_IN, pin 1, and VBAT_IO, pin 11, bypass.
- VDD_IN, VBAT and VBAT_IO stay on +3V3. VREG is never tied to +3V3.
  The SX1262 PA does not draw its transmit supply through L12.
- U4, the antenna connector and all unrelated placements remain unchanged.
  All 792 existing copper items are preserved, as are 217 old footprints;
  only C8 and C9 move. Three footprints are added.

TDK specifies 1.235 Ω maximum DCR and a 120 mA inductance-based rating
(at **50% inductance reduction**, not a continuous-current guarantee of
nominal inductance). Semtech's table lists 40 MHz resonance for this type;
verify impedance/current behavior in the final layout. The lower-DCR
MLZ2012N150L alternative was not selected: its 90 mA inductance rating is
below the datasheet's general 100 mA selection criterion, despite appearing
in that same recommended table.

Firmware must select `SetRegulatorMode(0x01)` in `STDBY_RC` after hardware
qualification. This document does not implement or validate that firmware.
Measure effective C9 capacitance, regulator startup, ripple, current and
radio sensitivity on the completed board. Nominal 3.3 V alone does not
prove +22 dBm across rail tolerance, load droop and temperature.

## Validation

- 218 schematic components; 222 board footprints including four mounts.
- 1,957 artifact-integrity assertions pass.
- 30 independent native-netlist power-contract checks pass. Four mutations
  (wrong inductor destination, grounded capacitor error, PA input on VREG,
  and the old 100 nF C9 value) are correctly rejected.
- Native schematic/PCB parity: **0 findings**.
- No new courtyard overlap, short, clearance or silkscreen findings.
- Native ERC: **30 findings** (24 isolated labels and six undriven pins).
- DRC: the same **four USB1 hole-clearance findings**.
- **491 unconnected items**; the added parts require routing.
- The existing CC1101 and local power continuity checks remain required.

The rebuild tool stages into `/tmp/handset-sx1262-power`; it never overwrites
an installed update. Source hashes and a full CAD backup guard installation.
`generated/sx1262-power-update.json` records the backup and preservation
counts. `generated/sx1262-power-bom.csv` is this step's subset, not a complete
manufacturing BOM. `check_handset_sx1262_power.py` reads native KiCad XML,
independently of the circuit generator.

## Remaining LoRa work

1. Finish the 32 MHz TCXO selection, DIO3 supply/filter, AC coupling and
   startup timing. XTA/XTB are not a working clock yet.
2. Complete PA choke/bypass, RF switch, matching/filter and antenna feed.
   C10 remains provisional, and J20 is not connected to a working frontend.
3. Route against a frozen stackup, with local returns and thermal vias;
   validate conducted RF, antenna matching and coexistence in the case.

The **Johanson 0900FM15K0039001E** 2.0 × 1.25 mm integrated matching/filter
is a researched candidate for 862–928 MHz, not an installed component.
Its reference still needs an external PA choke, PA bypass, RF switch and
antenna DC block. **BGS12WN6** is a switch candidate; ordering suffix/package,
truth table and land pattern must be verified before capture. The old
BGS12SN6 should not be copied blindly. The reference's 0.2 mm ground-via
layout also needs reconciliation with this board's fabrication rules.

## Manufacturer sources

- [Semtech SX1261/2 datasheet rev 1.2](https://files.waveshare.com/wiki/SX1262-XXXM-LoRaWAN-GNSS-HAT/DS_SX1261-2_V1.2.pdf),
  manufacturer-authored copy hosted by Waveshare: §§5.1.3–5.1.5, Table 5-3,
  and Fig. 14-2. Regulator topology, inductor recommendation and 470 nF bypass.
- [TDK MLZ2012M150WT000](https://product.tdk.com/en/search/inductor/inductor/smd/info?part_no=MLZ2012M150WT000):
  production status, dimensions, DCR and rated-current definitions.
- [TDK MLZ2012 catalog](https://product.tdk.com/info/en/catalog/datasheets/inductor_commercial_decoupling_mlz2012_en.pdf).
- [Murata C9 specification](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM155R61A474KE15-01A.pdf).
- [Semtech AN1200.40](https://cdn-reichelt.de/documents/datenblatt/A200/SX1262REFERENCE.pdf),
  manufacturer-authored distributor copy: TCXO reference and thermal-drift discussion.
- [Johanson AN101](https://www.johansontechnology.com/docs/4476/Johanson_AN101.pdf)
  and [IPD datasheet](https://www.johansontechnology.com/datasheets/0900FM15K0039/0900FM15K0039.pdf):
  compact frontend candidate and remaining external components.
