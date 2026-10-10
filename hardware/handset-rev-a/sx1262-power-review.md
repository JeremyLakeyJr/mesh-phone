# SX1262 core regulator support — 2026-09-24

Latest: [RF matching/switch capture](#rf-matching-and-switch-checkpoint--2026-10-08).

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

At the original regulator checkpoint, the **Johanson 0900FM15K0039001E** 2.0 × 1.25 mm integrated matching/filter
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


## Input supply routing checkpoint — 2026-10-08

U4.1 (VDD_IN), U4.10 (VBAT), U4.11 (VBAT_IO), C8, C75 and C76
are connected to the established +3V3 and ground networks. U4.2 and U4.20
join the already routed ground pins and exposed pad. C75 rotates 180 degrees
in place; all other footprint geometry stays unchanged. A front-layer supply
bridge clears the back-layer XTA clock trace.

The new main-rail feed is 0.5 mm wide and 76.695 mm long with ten layer
transitions. The local front-layer bridges are 0.3 mm wide, with 0.2 mm IC
pad escapes. These dimensions describe the implemented copper, not a supply
integrity approval. Review the feed/via impedance, VDD_IN bypass loop and
return geometry; measure rail droop and noise under transmit load before
release. Thermal stitching/spreading and the PA/RF frontend remain open.

All 16 physical pads in the input-supply/ground contract pass, including
continuity to established U1 rail/ground anchors. Six deliberately opened
pads are rejected, alongside the installed-board positive test. Existing
clock continuity/reference coverage and regulator checks pass. All 9,280
previous copper items and 596 previous connected pad groups are preserved;
191 copper items are added. Native DRC/parity are zero; open connections fall
from 231 to 220. The manufacturing gate enforces the new continuity contract
and retains the outstanding engineering blockers.

Evidence: `generated/sx1262-supply-routing.json`, `sx1262-supply-checks.json`
and `sx1262-supply-tests.json`. The previous board and placement are archived
at `archive/handset-before-sx1262-supply/eaa92c47fb4f/`. This checkpoint does
not release fabrication or power-up; the RF and TCXO qualification requirements
above still apply.


## RF matching and switch checkpoint — 2026-10-08

Ten components now capture the matching/filter and TX/RX switch topology.
**This is schematic capture with provisional front-side placement, not a
routed RF frontend.** The clock area occupies space near U4's RF pins;
final placement must be revised to follow the manufacturer layout geometry.
No existing footprint or copper is moved at this checkpoint.

| Ref | Selected part | Function |
| --- | --- | --- |
| U36 | 0900FM15K0039001E | Johanson integrated SX1262 TX/RX matching/filter |
| U37 | BGS12WN6E6327XTSA1 | Infineon SPDT, PG-TSNP-6-10 |
| R91/R92 | RC0402FR-07100RL, 100 Ω 1% | Control/supply series filters |
| C96/C97 | GRM155R71H102KA01D, 1 nF 10% X7R 50 V | Control/supply shunt filters |
| C98/C99/C100 | GRM1555C1H101JA01D, 100 pF 5% C0G 50 V | Antenna/TX/RX DC blocks |
| R93 | RC0402FR-07100KL, 100 kΩ 1% | Default-RX pull-down |

The [Johanson datasheet, revision 3.0](https://www.johansontechnology.com/docs/4856/IPD-0900FM15K0039001E_w8h4xck.pdf)
identifies the part and terminal mapping. Its
[AN101 reference](https://www.johansontechnology.com/docs/4476/Johanson_AN101.pdf)
connects U4 RFO/RFI_N/RFI_P to the matching device, with separate TX and RX
outputs feeding an SPDT. The PA choke and bypass remain external. RF trace
geometry and ground-via placement are part of the filter implementation;
component presence alone does not establish harmonic performance.

The [Infineon product page](https://www.infineon.com/part/BGS12WN6)
identifies the selected order code/package. The
[revision 2.9 datasheet](https://www.infineon.com/assets/row/public/documents/24/49/infineon-bgs12wn6-datasheet-en.pdf)
maps pins 1/2/3/4/5/6 to RF2/GND/RF1/VDD/RFIN/CTRL. Low selects RF1 (RX),
high selects RF2 (TX). DIO2 drives CTRL through R91; R93 supplies the default
low state. R92 feeds the switch from +3V3, independently of DIO3's TCXO rail.
The schematic power flag identifies that passive supply feed, not an
independent source. Firmware must select DIO2 RF-switch control and allow
switch power-up/settling before transmitting.

Infineon requires zero DC on all RF ports. All three ports therefore have
explicit series capacitors. The 100 pF value is an engineering starting
choice, reusing the specified C66 family, rather than a copied reference
value or a validated RF match. Measure DC isolation, loss and return loss in
the completed circuit. The control/supply 1 nF part is documented by
[Murata](https://www.murata.com/en-sg/products/productdetail?partno=GRM155R71H102KA01D).

Independent checks enforce exact net memberships, order codes, values and
both IC land patterns. Eight mutations catch swapped TX/RX ports, bypassed
DC blocks, swapped balanced input, wrong supply/ground and a short in place
of the RF capacitor. Native DRC/parity are zero; the SX1262 sheet has no ERC
findings. Overall ERC falls from 27 to 20. There are 275 components and
2,634 passing integrity assertions. Open connections rise from 220 to 245
because the new circuitry is deliberately still unrouted.

All 9,471 prior copper items, 269 prior footprints and 585 prior connected
pad groups are preserved. Evidence is in `generated/sx1262-rf-update.json`,
`sx1262-rf-checks.json` and `sx1262-rf-bom.csv`; the previous CAD is archived
at `archive/handset-before-sx1262-rf/f178a595df44/`.

**Remaining:** select/capture the PA choke and final VR_PA bypass values;
finish RF placement, routing and ground vias; qualify switch timing, DC
isolation, conducted power/harmonics, receive sensitivity, thermal behavior,
clock and antenna coexistence. The release gate retains these requirements.
No fabrication or power-up release is implied.


## PA choke and bypass checkpoint — 2026-10-08

The PA feed is now captured: `U4.24 (VR_PA)` feeds L13, whose other end
joins `U4.23 (RFO)` and `U36.1`. C10 and C101 connect from VR_PA to ground,
on the supply side of the choke. This rail remains separate from the core
VREG output and +3V3. No extra power flag is needed for U4's PA output.

| Ref | Selected part | Value / function |
| --- | --- | --- |
| L13 | LQW15AN47NG80D | 47 nH ±2%, 0402 wirewound PA choke |
| C10 | GRM155R71E473KA88D | 47 nF ±10%, X7R, 25 V; replaces provisional 100 nF |
| C101 | C1005C0G1H470J050BA | 47 pF ±5%, C0G, 50 V; high-frequency PA bypass |

The values follow the manufacturer's
[RAK4270 schematic](https://downloads.rakwireless.com/LoRa/RAK4270/Hardware-Specification/RAK4270_Schematic.pdf):
L1 is 47 nH and the VR_PA shunts C32/C33 are 47 nF/47 pF.
[Johanson AN101](https://www.johansontechnology.com/docs/4476/Johanson_AN101.pdf)
also shows the external PA choke and two bypass capacitors around its IPD.
**This combines a documented SX1262 PA baseline with the Johanson topology;
it is not a qualified reference BOM/layout for this assembled frontend.**
The chosen supplier parts are engineering selections; the RAK schematic
establishes nominal values, not these exact order codes.

[Murata's component list](https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/static-model/component-list-ind-s-2602.ashx?cvid=20260515010000000000&la=en-gb)
identifies LQW15AN47NG80. Its
[manufacturer-authored data sheet, mirrored by Arrow](https://static6.arrow.com/aropdfconversion/dad745742b96a55e3970cd4197a24f0c7dc60c0/lqw15an47ng80.pdf)
lists the D tape suffix, 440 mA temperature-rise rating and 0.648 ohm maximum
DC resistance. These are component limits, not PA current/thermal approval.
C10's value/dielectric/rating are recorded in
[Murata's MLCC list](https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/dynamic-model/component-list-d-mlcc-2506.ashx?cvid=20250805040419000000&la=en).
[TDK's C101 product page](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1005C0G1H470J050BA)
identifies the selected 0402 part. Confirm procurement status and assembly
land patterns when the BOM is frozen.

C10 keeps its previous back-side position. L13/C101 have provisional
front-side positions beside the RF circuit; no PA copper is added. Final
layout must bring the choke/bypass next to U4's RF pins, with short ground
returns and the required RF ground geometry. The existing TCXO occupies
nearby back-side space, so resolve that placement conflict before routing.
Do not route this provisional arrangement as if it were the final RF layout.

The independent PA checker enforces exact VR_PA/RFO membership, bypass
grounds, values, MPNs and PCB/netlist agreement. Eleven mutations reject
wrong supply rails, the core-switch node, bypasses on the RFO side, a wrong
IPD connection, the old C10 value, wrong choke value/package and missing MPN.
Both the integrity gate and manufacturing gate enforce the PA contract;
qualification remains an explicit manufacturing blocker.

There are 277 components and 2,644 passing integrity assertions. Native DRC,
schematic parity and placement findings are zero; overall ERC remains 20
and the SX1262 sheet is clear. Open connections increase from 245 to 249
because the new PA parts are still unrouted. All 9,471 existing copper items,
279 existing footprint geometries and 623 existing connected pad groups are
preserved. Only C10's value/MPN changes among existing PCB components.

Evidence: `generated/sx1262-pa-update.json`, `sx1262-pa-checks.json` and
`sx1262-pa-bom.csv`. The previous CAD is archived at
`archive/handset-before-sx1262-pa/ba78918224a3/`.

**Next:** resolve RF/TCXO placement, route PA and RF paths against the chosen
stackup, complete ground/thermal geometry, and clear remaining circuit and
routing blockers. PA current, supply droop, RF matching, power/harmonics and
receive sensitivity require qualification. Fabrication and power-up remain
unreleased.


## Local PA/RF routing checkpoint — 2026-10-09

The TCXO has moved west of U4 to clear its RF pins. L13, C10, C101 and U36
are now on the back layer beside U4. The PA feed, bypass returns and
RFO/RFI_N/RFI_P connections to U36 are routed. **U36 ground lands and the
downstream switch/antenna paths are still incomplete; this is not an
operational RF frontend or a fabrication release.**

Y3, R90 and C94 move together while C95 stays fixed. The clock signal path
remains entirely on B.Cu without signal vias: 8.092 mm, below the unchanged
10 mm check limit. All 14 clock pads and 276 In2 ground-reference samples
pass. DIO3 power now crosses the local area on In1.Cu; it remains isolated
from the main supply. Two local ground-zone extensions retain the adjacent
reference plane. TCXO amplitude/startup/supply qualification is unchanged.

The unrouted IR connector J25 moves from (103,35) to (103,33.7) mm; R49 and
C44 move to (101,38.4) and (98.8,38.6) mm. These changes clear the oscillator
courtyard while retaining connector pinout and nets. Review case-harness
reach and assembly access before mechanical release. R10 moves to
(116.8,37) mm. The U4 VDD_IN escape/via is rerouted locally to clear the PA
choke; input-supply continuity still passes against the established anchors.
All other footprint geometries stay unchanged.

| Routed net | Total trace length | Geometry |
| --- | --- | --- |
| SX_VR_PA | 4.2094 mm | Local B.Cu choke/bypass feed, no vias |
| SX_RFO | 4.5287 mm | B.Cu input route including choke branch, no vias |
| SX_RFI_N | 3.0924 mm | B.Cu input fanout, no vias |
| SX_RFI_P | 3.0924 mm | B.Cu input fanout, no vias |

These are sums of CAD trace lengths, not electrical lengths. RFO includes
its PA choke branch. The RF fanouts use 0.2 mm traces with native clearance
checks; the receive routes have equal CAD lengths. **Neither equal length
nor continuity validates RF impedance.** The fanouts are routing candidates
pending adaptation/validation against the selected JLC04161H-7628 stackup.
Do not treat them as approved 50-ohm transmission lines.

The [Johanson layout guidance](https://www.johansontechnology.com/docs/4856/IPD-0900FM15K0039001E_w8h4xck.pdf)
requires transmission-line geometry for the actual PCB material/thickness
and emphasizes ground-via placement for harmonic attenuation. Its reference
shows 0.2 mm ground vias; reconcile that geometry with the current board
rules and fabricator before completing U36 grounds. The relocated U36 is a
layout candidate, not a substitute for this review. Adjacent CC1101/GNSS
parts constrain the downstream switch/antenna placement.

Fourteen local PA/RF contract pads pass continuity, including both bypass
returns to the established ground anchor. All 375 sampled In2 ground
reference points under the RF input traces pass. Nine regression cases
cover the installed board, six isolated pads, a wrong RF layer and a removed
reference plane. The five existing clock regression cases also pass.
The RF footprint checker now accounts for back-side mirroring while keeping
the same terminal positions, dimensions and pin-net requirements.

The change replaces 28 explicitly identified clock/local-supply copper items
and adds 49. All other 9,443 copper items and all 627 previously connected
pad groups are preserved; total copper items are 9,492. The manifest lists
every removed item. Native DRC/parity and placement findings remain zero.
All 2,644 integrity assertions pass; 277 components and 20 ERC findings are
unchanged. Unconnected items fall from 249 to 240.

Evidence: `generated/sx1262-local-rf-routing.json`,
`sx1262-local-rf-checks.json`, `sx1262-local-rf-tests.json`, and refreshed
clock/supply checks. Previous board/placement evidence is archived at
`archive/handset-before-sx1262-local-rf/9a212933222f/`.

**Next:** resolve RF transmission-line and U36 ground-via geometry, then
finish switch/DC-block/antenna placement and copper. Complete thermal,
supply, clock, conducted power/harmonics, sensitivity and coexistence
qualification. The manufacturing gate retains these open requirements.


## RF ground and impedance checkpoint — 2026-10-10

All five U36 ground lands (2, 5, 7, 9, 10) now connect to local B.Cu ground
and established ground planes. Each has a nearby through via: 0.45 mm land,
0.2 mm hole, 0.125 mm nominal annular width, explicitly tented on both faces.
The longest pad-center to nearest-via-center distance is 0.6 mm. No component
moves in this checkpoint. Detailed return geometry and harmonic performance
still require validation; this is not an RF performance sign-off.

The [Johanson reference layout](https://www.johansontechnology.com/docs/4856/IPD-0900FM15K0039001E_w8h4xck.pdf)
shows 0.2 mm ground vias and calls out their placement as important to harmonic
attenuation. The implemented five-via/ground-pour arrangement follows those
constraints as a layout candidate, not a claim to reproduce an unavailable
manufacturer CAD file exactly. Confirm the intended hole definition and
final return geometry with the manufacturer/fabricator before release.

[JLCPCB's published drilling capabilities](https://jlcpcb.com/capabilities/pcb-capabilities)
list 0.2 mm as the preferred minimum via hole and describe larger via lands
for small-hole processing. The selected 0.45 mm land retains more than the
board's 0.1 mm minimum annulus. The nominal board is still 1.6 mm/four layers;
this change does not introduce blind vias or via-in-pad. Hole tolerance,
plating, tenting and assembly acceptance remain fabricator review items.

KiCad's global floors are now 0.45 mm via diameter and 0.2 mm hole so the RF
vias can pass. **The new `generated/handset.kicad_dru` is required:** general
rules retain the prior 0.5 mm via / 0.3 mm hole minimums. Only GND vias fully
enclosed in the named `SX1262 RF grounding` area receive the exact
0.45/0.2 mm exception. Copper/hole clearances and minimum annular width are
unchanged. The checker rejects missing or weakened rule files. Native DRC
mutation cases confirm that a small signal via in the area and a small GND
via outside it are rejected, as is a larger drill within the RF exception.

The nominal drill edges stay at least 0.15 mm outside all matching-device
lands; a regression case rejects a drill moved onto a ground land. Fabricator
drill-position and finished-hole tolerances still require review.

The old 14.1 mm front-layer 3V3 segment crossed the new via locations. It is
replaced by a 17.4154 mm path around the RF return area at the same 0.5 mm
width. Input-supply continuity remains intact. Qualify the additional feed
length and its supply impedance under transmit load; continuity and native
clearance do not establish current/thermal performance.

### Downstream 50-ohm routing target

The selected [JLC04161H-7628 stackup](https://jlcpcb.com/impedance) retains
0.2104 mm outer dielectric and 35 micrometre outer copper. A reproducible
2-D finite-volume quasi-TEM screen uses nominal Dk 4.4 and an approximate
solder-mask model, consistent with the existing USB screening approach.

| Model at 0.34 mm trace width | Estimated single-ended impedance |
| --- | --- |
| 5 micrometre grid, 4 × 1.5 mm domain | 49.805 ohms |
| 2.5 micrometre grid, same domain | 49.899 ohms |
| 5 micrometre grid, 6 × 2.25 mm domain | 50.216 ohms |

Grid refinement changes the result by 0.094 ohm; expanding the finite
boundary changes it by 0.411 ohm. These are numerical sensitivity checks,
not material-tolerance or impedance-coupon evidence. The same isolated-line
model gives 63.755 ohms for a 0.2 mm trace, reinforcing that the existing
short IC fanouts cannot simply be described as verified 50-ohm routing.
That isolated-line result does not model the coupled RX pair or the actual
complex chip-port impedances.

A new **RF 50 ohm target** net class records a 0.34 mm routing width only for
SX_TX_MATCH, SX_TX_AC, SX_RX_MATCH, SX_RX_AC, SX_ANT_AC and LORA_RF_50R.
The radio's RFO/RFI_N/RFI_P fanouts remain outside this class. The model
assumes a uniform isolated line above a continuous reference plane; pads,
bends, near coplanar copper, vias, device matching and short transitions
need separate review. No existing signal copper is widened at this checkpoint.
The downstream switch/antenna layout must implement and validate these
transitions rather than blindly apply the nominal trunk width everywhere.

Evidence: `generated/rf-impedance-estimate.json` records inputs, results,
limitations and the estimator hash. Reproduce with
`scripts/estimate_handset_rf_impedance.py --width .34`, add `--step .0025`
for refinement or `--span 3 --height 2.25` for the expanded domain.
Fabricator field-solver/coupon evidence and assembled RF qualification remain
required; no order or supplier approval is implied.

### Verification and remaining work

Thirteen regression cases pass: the installed board, five isolated ground
lands, missing tenting, drill overlap with a land, three native drill-rule mutations, missing rules
and weakened general limits. The full project integrity checks pass with
2,644 assertions, 277 components, zero native DRC/parity/placement findings
and unchanged 20 ERC findings. Unconnected items fall from 240 to 235.

All 281 footprint geometries, 9,491 unreplaced copper items and 618 previously
connected pad groups are preserved. One supply segment is replaced and 15
copper items are added, for 9,506 total. Evidence is in
`generated/sx1262-rf-ground-routing.json`, `sx1262-rf-ground-checks.json`
and `sx1262-rf-ground-tests.json`; the previous board/project is archived at
`archive/handset-before-sx1262-rf-ground/ca67f1aee4ed/`.

**Next:** finish RF switch, DC-block and antenna placement/copper, then review
all RF transitions and ground geometry against the reference design. Keep
fabrication blocked pending RF/supply/clock/thermal qualification and the
other recorded electrical/mechanical blockers.

## Switched RF routing checkpoint — 2026-10-10

**CAD copper is captured; not fabrication or RF performance approval.** The
matching device now connects through C99/C100 to the TX/RX switch, then through
C98 to J20. DIO2 control, its RC filter and default-RX pull-down, filtered +3V3
switch supply, bypass returns and both antenna-connector ground pads are routed.
No schematic values, pin assignments or part selections change.

U37 and its eight passives move within the available front-layer area. The
matching device and connector remain on the back. Three tented 0.5 mm land /
0.3 mm drill through vias transfer TX, RX and antenna signals between faces;
the ordinary drill rules apply. The matching-device 0.45/0.2 mm GND exception
remains limited to its previously checked area. GNSS and existing USB circuitry
retain their placement and copper.

The [Infineon BGS12WN6 datasheet, revision 2.9](https://www.infineon.com/assets/row/public/documents/24/49/infineon-bgs12wn6-datasheet-en.pdf)
requires zero DC on the RF ports and identifies CTRL low with RX/RF1, high with
TX/RF2. All three 100 pF DC blocks and the default-low control bias remain in
that topology. The [Johanson reference](https://www.johansontechnology.com/docs/4856/IPD-0900FM15K0039001E_w8h4xck.pdf)
still governs matching-device ground and port-layout review; the changed layer
transitions require separate RF analysis and measurement.

### Geometry and reference checks

| Net | Planar trace length | Signal vias |
| --- | ---: | ---: |
| SX_TX_MATCH | 3.5105 mm | 1 |
| SX_TX_AC | 2.2586 mm | 0 |
| SX_RX_MATCH | 1.9524 mm | 1 |
| SX_RX_AC | 2.5700 mm | 0 |
| SX_ANT_AC | 4.3875 mm | 0 |
| LORA_RF_50R | 6.3381 mm | 1 |

Lengths exclude component internals and via barrels. Trunks use the previously
screened 0.34 mm width, with 0.2 mm matching-device escapes and 0.15 mm local
switch neck-downs. Neither the narrow sections nor the three transitions are
qualified 50-ohm geometry. Bends, pads, coupling, loss and parasitics remain
part of RF validation; the uniform-line screen does not cover them.

The checker samples the adjacent In1 ground under front traces and In2 under
back traces every 0.1 mm, at the center and 0.1 mm beyond each trace edge.
All 753 samples pass: 103 points inside the explicitly bounded same-net
signal-via antipads are exempt, and no other reference gaps remain. Filled
return copper extends the existing reference planes. The nearest connected
ground vias are 0.6500, 0.8732 and 0.8062 mm from the TX, RX and antenna
transitions respectively. The 1.25 mm checker bound is a layout guard, not an
RF return-inductance qualification. Nominal signal drill edges remain at least
0.15 mm outside numbered lands; actual hole and registration tolerances still
need fabricator review.

The main 0.5 mm front-layer supply feed detours around the RF area. Its
previous 17.4154 mm path is now 20.1225 mm; the width is unchanged and a
0.25 mm branch feeds R92. Confirm the extra feed impedance and thermal behavior
under load. The C8 ground via moves from (115.6, 34.1) to (115.6, 33.6) mm,
shortening its ground stub to clear the DIO2 escape. Supply, clock, local PA/RF
and matching-device ground checks continue to pass.

### Evidence and remaining work

Seventeen regression cases cover the installed layout, twelve disconnected
pad controls, missing signal-via tenting, removed reference planes, missing
transition ground returns and an unreviewed trace width. The full project
checks retain 2,644 passing integrity assertions, 277 schematic components,
zero native DRC/parity/placement findings and 20 existing ERC findings.
Unconnected items fall from **235 to 216**.

All 613 previously connected pad groups, 272 unmoved footprints and 9,501
unreplaced copper items are preserved. Five copper items are replaced and 86
are added, giving 9,587 total. The previous board, project/rules, placement and
verification files are archived at
`archive/handset-before-sx1262-switch/6e88163d5783/`. Current evidence:
`generated/sx1262-switch-routing.json`, `sx1262-switch-checks.json` and
`sx1262-switch-tests.json`. Both the full PCB gate and manufacturing release
check run the new live copper checks; RF qualification still blocks release.

**Next fabrication work:** place and route the CC1101 clock and local supply
network, then its RF matching/filter and antenna path. Complete remaining
routing and ERC corrections, mechanical/BOM review and fabricator DFM before
prototype release. The SX1262 still needs stackup/transition review, switch
DC and timing checks, conducted power/harmonics, sensitivity, antenna matching,
coexistence and clock/supply/thermal qualification on assembled hardware.
