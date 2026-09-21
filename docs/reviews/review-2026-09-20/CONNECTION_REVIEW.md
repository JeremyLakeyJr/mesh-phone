# Owasso1 electrical review — 20 September 2026

**Release status: DO NOT FABRICATE OR POWER THE ORIGINAL DESIGN.**

The original layout passes geometric DRC, but its circuit has faults that can
damage a battery and several faults that prevent normal operation. DRC checks
copper against the supplied netlist; it cannot establish that that netlist is a
correct circuit. Most original IC symbols are generic passive connectors, so
their original zero-error ERC result also does not validate IC pin functions.

The user's hardware is not yet purchased. The target is a US phone; the carrier
is undecided. Expansion modules will be exchanged with power off.

## Files and scope

- Original: `../owasso1.kicad_pro`. Existing placements are preserved.
- Engineering revision: `../revF-gps-expansion/owasso1.kicad_pro`.
- Revision F adds GPS, a protected rear expansion port, MCU support, and the
  verified connection corrections listed below. It is **not a release package**.
- Existing `../fab-output/` and `../gerbers/` predate this review and must not be
  ordered. No new manufacturing package is released by this work.
- Baseline exported netlist, ERC, and parity DRC are saved in this directory.

## Critical findings and correction status

| Circuit | Verified problem in original | Revision F status |
|---|---|---|
| Battery/USB switch | SW1.1 is VBUS5V and SW1.2 is VBAT. Closing these contacts directly connects USB 5 V to the battery/charger BAT net. | Corrected to BAT_CHARGE → switch → VBAT system rail. This only removes this direct connection; it does not fix the rest of the charger/protection design. |
| MCU enable | U1.3/EN is marked unconnected. | Added 10 kΩ pull-up, 1 µF capacitor and RESET button. |
| MCU SPI | U1.28/29/30 are GPIO35/36/37, used internally by octal PSRAM on N16R8. | Moved SCK/MOSI/MISO to GPIO12/13/14 (module pads 20/21/22). |
| LoRa chip select | SX1262_CS uses module pad 16, GPIO46, which is input-only. | Moved CS to GPIO21, module pad 23. |
| CC1101 GPIOs | CS/GDO0 use boot-strapping GPIO45/GPIO0. | Moved CS/GDO0 to GPIO47/GPIO48, module pads 24/25. GPIO0 now has BOOT button and 10 kΩ pull-up. |
| Keypad expander | PCF8574T pins 1–3 are address inputs, but were wired to keypad rows; pins 10–12 are I/O ports, but were grounded. | Address pins grounded for 0x20; rows on pins 4–7, columns on pins 9–12. |
| Display controls | LCD_RESET, TP_RESET and TOUCH_INT have only one endpoint. | Assigned GPIO16, GPIO17 and GPIO8 (module pads 9, 10 and 12). |
| I²C | No explicit host pull-ups. Some module boards might provide them, but this is not a reliable design contract. | Added 4.7 kΩ SDA/SCL pull-ups to 3V3. Check effective resistance with populated daughterboards. |
| Battery protection | Q1.2/.3/.5/.6 all connect to the same GND. The battery negative and system ground are directly common; there is no series protection disconnect. FS8205A package identification also needs correction. | **Unresolved.** Do not rely on this circuit for cell protection. |
| Charging | TP4056 CE and TEMP are unconnected, the exposed-pad schematic contract was missing, and no power-path/load-sharing circuit is present. A running load on BAT interferes with charge termination. | Exposed pad added to schematic contract. **Charger, temperature sensing and power-path redesign remain required.** |
| USB input current | R1 = 1.2 kΩ nominally programs approximately 1 A charging, without a circuit to determine allowable USB source current or account for the phone load. | **Unresolved.** USB-C Rd resistors alone do not authorize a 1 A load from every source. |
| 3.3 V supply | U5 is only named “3V3-LDO”; no exact part is selected. Pin 3 is unconnected. No established dropout, current, enable or thermal design exists. | **Unresolved.** Choose and design a supply for the combined ESP32, display, radios, GPS and expansion load across the battery range. |
| 5 V boost | TPS61023 has L1 approximately 54 mm away; input/output capacitors and feedback divider are also far away. This is not a viable switching-regulator layout. The 180 kΩ/27 kΩ divider targets approximately 4.6 V, not 5 V. | **Unresolved.** Redesign locally around the IC and select a rated inductor/capacitors after selecting the modem power interface. |
| Capacitors | C1 is labelled 1000 µF but assigned a ceramic 1206 footprint; no matching purchased part is defined. | **Unresolved BOM/footprint selection.** Do not order from value text alone. |
| US LTE | A7670E is a regional modem with an unsuitable band set for a general US design. Carrier voice/VoLTE acceptance and firmware are undecided. The 23-pin third-party carrier contract lacks a verified manufacturer schematic. | **Not approved.** Select a US-compatible, documented modem/carrier and verify its current bursts, UART levels, audio and SIM interface. |
| SIM | J10 CLK/RST/IO/DET have no modem counterpart; SIM VCC is tied to host 3V3. | **Unresolved.** Use the selected modem's SIM supply/interface, or its onboard SIM socket; do not parallel two sockets. |
| LoRa RF control | TXEN, RXEN, DIO2 and DIO3 remain one-pin nets. | **Unresolved.** Verify the specific Ra-01SH RF switch/TCXO wiring and firmware policy. SPI CS correction alone is insufficient. |
| IR transmitter | TSAL6200 is assigned an 0805 footprint and is connected directly between GPIO42 and GND without a series resistor/driver. | **Unresolved.** Select a matching LED and design its resistor/transistor stage. |
| IR receiver | IR_RX is only connected to U7. | **Unresolved MCU assignment.** |
| Fuel gauge | U6 has no SDA/SCL connections; its four-pin header is not a verified MAX17048 breakout contract. | **Unresolved.** Use a documented breakout or a real IC symbol/footprint and reference circuit. |
| RFID | RFID_RX/RFID_TX are one-pin nets, with no verified level conversion. | **Unresolved.** Verify the exact RDM6300 breakout and logic voltage. |
| USB/RF routing | Existing USB pair and LoRa antenna trace were autorouted without a demonstrated controlled-impedance stackup. External-port ESD protection is incomplete. | **Unresolved signal-integrity and protection review.** |

The current LTE_RI, trackball interrupt, keypad interrupt, status and SIM-detect
policies also need firmware decisions. Some status pins can legitimately remain
unused, but they must not be confused with functioning host interfaces.

## GPS and rear expansion

See `../revF-gps-expansion/INTERFACES.md` for pin tables and power-off handling.
GPS uses a MAX-M10S-00B-01, a passive antenna connector, UART series resistors,
10 µF/100 nF bypass capacitors and a PPS connection. VCC and V_IO use 3.3 V;
VIO_SEL, SAFEBOOT and V_BCKP are intentionally open. No direct LiPo connection
is made to the GPS. Without a backup supply, expect a cold start after power-off.

The GPS and expansion circuitry is connected in both schematic and PCB netlist.
This does not resolve the inherited 3.3 V source defect. RF antenna placement,
cellular coexistence and supply ramp/current behavior require hardware testing.

## What the checks establish

Original KiCad 10.0.6 results: 0 geometric DRC violations, 0 unconnected copper
items, **70 schematic-parity findings**, and **107 ERC warnings**. Direct
manufacturer pin review found the critical faults above despite those counts.
Konnect's heuristic design review completed with warnings, but did not identify
the generic-symbol pin-contract problems; it is supplemental evidence only.

Revision F retains existing part positions, orientations, sides and keypad
geometry. Obsolete copper on changed nets was removed before rerouting. A
separate netlist validation checks the corrected GPIOs, keypad pin order,
GPS UART direction and expansion pin order. Final tool counts are recorded in
`../revF-gps-expansion/verification-summary.json`; read them together with the
open electrical blockers, never as an electrical approval.

Final Rev F checkpoint: 608/608 independent net/placement assertions passed;
native DRC has 0 errors, 0 unconnected items and 0 schematic-parity findings.
Five footprint-library mismatch warnings remain (J10, USB1, U1, J14, J3).
Native ERC has 2 power-input errors and 24 isolated-label warnings. These have
not been hidden with power flags or DRC exclusions. The original fabrication
clearances were retained. New reset-circuit ground vias also need a final
via-in-pad assembly-process review or relocation before release.

## Required before release

1. Select the US modem/carrier and firmware, and establish the peak-current and
   logic-voltage budgets. Carrier acceptance is separate from LTE band support.
2. Replace the charger/protection/supply placeholder circuits with verified
   designs, including cell temperature sensing and adequate battery connector,
   switch, copper and regulator ratings. Size the supplies for concurrent loads.
3. Complete the remaining IR, radio, fuel-gauge, RFID and SIM interfaces.
4. Replace generic IC connector symbols with correct electrical symbol types;
   clear ERC, schematic parity and geometric DRC without blanket waivers.
5. Finish controlled-impedance USB/RF routing and all antenna keepouts against
   the chosen fabrication stackup. Check battery, display, rear connector and
   module heights in the enclosure, including mating cable access.
6. Bring up a prototype with a current-limited supply before connecting a cell.
   Test rail sequencing, charge termination/temperature behavior, modem bursts,
   USB enumeration, display/touch, keypad, all radios, GPS acquisition, module
   operation and real carrier voice calls. This has not been done here.

## Primary references

- [Espressif WROOM-1/-1U datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf): module pin numbers, N16R8 PSRAM restrictions and GPIO capabilities.
- [NXP PCF8574 datasheet](https://www.nxp.com/docs/en/data-sheet/PCF8574_PCF8574A.pdf): SO16 address and I/O pin assignments.
- [u-blox MAX-M10S datasheet](https://content.u-blox.com/sites/default/files/MAX-M10S_DataSheet_UBX-20035208.pdf) and [integration manual](https://content.u-blox.com/sites/default/files/MAX-M10S_IntegrationManual_UBX-20053088.pdf): GPS pinout, supply and passive-antenna reference design.
- [TI TPS2553 datasheet](https://www.ti.com/lit/ds/symlink/tps2553.pdf): rear-port current-limited switch and ILIM resistor.
- [JST GH connector drawing](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf): keyed, locking connector and matching housing.
- [Waveshare display documentation](https://www.waveshare.com/wiki/3.5inch_Capacitive_Touch_LCD): display/touch interface.
- [TI TPS61023 datasheet](https://www.ti.com/lit/ds/symlink/tps61023.pdf): regulator feedback equation and layout requirements.
- [SIMCom A7670 family band table](https://cn.simcom.com/product/A7670X.html): regional modem differences; not carrier approval.
- [Ai-Thinker Ra-01SH documentation](https://docs.ai-thinker.com/Ra-01SH/): exact module variant and RF controls still require completion.
- [Taoglas FXP611 antenna](https://www.taoglas.com/product/cloud-fxp611-gps-glonass-compass-flexible-pcb-2/): proposed enclosure-mounted passive GNSS antenna.
