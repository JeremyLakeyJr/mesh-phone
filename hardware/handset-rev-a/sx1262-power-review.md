# SX1262 core regulator support — 2026-09-24

Follow-up: the [TCXO clock checkpoint](#tcxo-clock-checkpoint--2026-10-08) below
adds the clock circuit and its local routing. The original regulator review is
retained as history.

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

1. Qualify the captured TCXO clock below: maximum output amplitude, DIO3
   supply behavior, startup timing and temperature drift remain open.
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


## TCXO clock checkpoint — 2026-10-08

The clock circuit and local copper are now present. The PA feed, matching/filter,
RF switch, antenna path and remaining radio power/ground are still incomplete.
This does not release the radio or handset for fabrication.

| Ref | Selected part | Connection |
| --- | --- | --- |
| Y3 | ECS-TXO-32CSMV-320-AN-TR | DIO3-powered 32 MHz clipped-sine TCXO |
| R90 | RC0402FR-07220RL, 220 Ω 1% | Series clock resistor |
| C94 | GRM155R71C104KA88D, 100 nF | TCXO supply bypass |
| C95 | GRM1555C1H100JA01D, 10 pF C0G | Series coupling into XTA |

[ECS’s product page](https://ecsxtal.com/products/oscillators/surface-mount-oscillators/ecs-txo-32csmv-320-an-tr/)
lists the selected 32 MHz AN option. Its
[series datasheet](https://ecsxtal.com/store/pdf/ECS-TXO-32CSMV.pdf)
specifies a 1.7–3.465 V supply, 2.5 mA maximum consumption at this frequency,
2 ms maximum startup and 0.8 Vpp **minimum** output. The 0.5 ppm temperature
option is not total frequency accuracy: initial tolerance, aging and other
terms still apply. The audited footprint follows its 1.4 × 1.2 mm lands on
2.2 × 1.6 mm centers; pins 1 and 2 are both ground, 3 is output, 4 is supply.
The older Abracon ASVTX/ASTX-13 datasheet is marked EOL and was not selected.

Semtech DS rev 1.2 §4.1.4 specifies the 220 Ω / 10 pF series network and an open
XTB. DIO3 is reserved for the regulated TCXO supply. The specialized U4 symbol
models this selected supply function; other pin functions are retained.
The proposed setting is 1.8 V (`tcxoVoltage=0x02`) with a provisional 5 ms delay
(`0x000140` at 15.625 µs/tick, §13.3.6). VBAT must exceed the programmed voltage
by 200 mV. These settings require target integration and measurement.

**Open qualification:** Semtech requires TCXO output no greater than 1.2 Vpp,
but ECS’s series sheet supplies no maximum. Obtain a supplier guarantee or
appropriate measurement evidence before approving this interface. Confirm
loaded startup, DIO3 ramp/current, temperature drift, phase noise and radio
sensitivity; the series RC network alone is not proof of compliance.

The routed clock path is 6.789 mm on B.Cu with no signal vias. Two local inner
GND extensions provide its return; 228 sampled corridor points pass. All 14
required physical pads pass continuity. Five netlist mutations and five copper
regression cases detect wrong wiring, capacitance, open pads and a missing
reference plane. Existing component locations and all 9,238 previous copper
items remain intact; all 601 previous connected pad groups remain connected.
Only U12’s reference text moves to B.Fab to clear the new lands.

Native DRC/parity are zero. The three former isolated clock labels are resolved:
ERC falls from 30 to 27. There are 265 components, 2,560 integrity assertions
and 237 remaining unconnected items. Evidence is in
`generated/sx1262-clock-update.json`, `sx1262-clock-checks.json`,
`sx1262-clock-tests.json` and the clock BOM subset. The source checkpoint is
archived at `archive/handset-before-sx1262-clock/7d4b34c23603/` in the repository
root. The manufacturing gate retains clock qualification as an explicit blocker.


## Regulator routing checkpoint — 2026-10-08

The local DC-DC switching and VREG paths are routed on B.Cu without vias.
L12 rotates 180 degrees in place so its switching terminal faces U4.9;
its VREG terminal joins U4.7 and C9.1. C9.2 returns through a new ground
via into the existing inner return. U4.8 and the exposed pad U4.25 join
the established U4.5 ground connection. This establishes electrical
continuity; it does not qualify the final thermal or switching layout.

Fifteen copper items are added. All 9,265 previous tracks/vias and all
602 previous connected pad groups are preserved; L12 is the only rotated
footprint. Independent checks cover the three net groups, back-layer-only
regulator routing, short trace limits and six deliberately disconnected
pads. The existing clock continuity and reference-plane checks still pass.
Native DRC and schematic parity remain zero; open connections fall from
237 to 231. ERC remains at 27 findings.

Evidence: `generated/sx1262-regulator-routing.json` and
`generated/sx1262-regulator-checks.json`. The previous board and placement
are archived at `archive/handset-before-sx1262-regulator/e36b11dc7446/`.
Both the board-check script and manufacturing gate enforce this contract.

**Still open:** U4 input supply/bypass distribution, remaining ground pins,
thermal ground stitching, PA feed and RF frontend. Review loop return
geometry in the completed layout and measure regulator startup/ripple and
RF performance. The TCXO qualification requirements above still apply.
This checkpoint does not release fabrication or authorize power-up.
