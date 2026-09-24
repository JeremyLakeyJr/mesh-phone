# Handset physical population checkpoint — 22 September 2026

**DO NOT FABRICATE OR POWER.** This replaces empty placement allowances with
real schematic parts and PCB footprints. It does not release a working phone.
Use `generated/verification-summary.json` for current counts; the original
20 September review's numbers describe different boards.

Subsequent work: [the 3.3 V local routing checkpoint](3v3-layout-review.md)
completes 18 copper connections, reducing board-wide unconnected items to 473.
The counts below retain the earlier population checkpoint for comparison.

## Verified checkpoint

The saved handset contains 170 components, 68 added in this population update.
`bash scripts/check_handset_pcb.sh` passes 1,619/1,619 integrity assertions,
with zero schematic/PCB parity findings, zero detected placement errors and
zero remaining reservation zones. Native checks still report four USB1
hole-clearance findings, 46 ERC findings and 491 unconnected items.
The ERC findings comprise 34 isolated labels, three undriven power pins,
seven undriven input pins and two pin-to-pin conflicts.

`python scripts/check_handset_release.py` correctly refuses release with
11 open engineering blockers. Passing the integrity command only establishes
the checked structural properties; it is not a release approval.
See [the earlier connection review](../../docs/reviews/review-2026-09-20/CONNECTION_REVIEW.md)
for the original-board and revF findings, and
[release-blockers.json](release-blockers.json) for the handset's outstanding work.

The ESP32 thermal-pad footprint now uses 0.3 mm drills with 0.6 mm copper;
the assembler must still review via filling/capping. SW19's relocated position
also requires the case power-switch opening to be reconciled.

## Replaced areas

| Former reservation | Implemented parts | Work still required |
|---|---|---|
| NFC | U13 ST25R3916B-AQET, Y1 ABM8-27.120MHZ-B2-T, C31–C39, R40 | Antenna/receiver matching, oscillator load verification, RF/layout validation |
| LF support | U18 SN74AHCT125PWR, U19 SN74LVC1G17DBVR, C45/C46, R50/R51 | Clock, analog reference, resonant coil and host return/timing allocation |
| IR | Q1 AO3400A, R46–R49, C44, J24/J25 | Install TSAL6400 emitter and TSOP38438 receiver in case; validate optical alignment and firmware |
| Storage | J23 Hirose DM3D-SF, R43–R45, C42/C43 | Card insertion clearance and routed SPI validation |
| Expansion protection | U14 TPS2553DBVR, U15/U16 TPD4E05U06DQAR, R41/R42, C40/C41 | Routed short return paths, current-limit test, power-off accessory policy |
| Display | J26 FH12A-50S-0.5SH(55), Q2 AO3400A, R52–R59, C47–C49 | Confirm CTP purchase configuration, cable stack, supply tolerances and firmware |
| Modem power | U20 TPS63070RNMR, L4 XFL4020-152MEC, Q3/Q4, R60–R64, C50–C55 | Converter layout, burst tests, cutoff behavior, modem adapter and carrier qualification |

U17 adds USB data/CC ESD protection. U12 MAX-M10S and J20–J22 were already
populated before this checkpoint. L1–L3 now use XFL4020-471MEC, -102MEC
and -222MEC respectively, with actual 4 mm inductor land patterns.

These are added to both native schematics and PCB net assignments, not merely
illustrations. Original key routes and unrelated placements are preserved.
Changes made to resolve interference are recorded in the migration JSON files;
snapshots are under `archive/handset-before-population`, `handset-before-display`
and `handset-before-modem-supply` at the repository root.

## Electrical contracts and limitations

- U14 uses a 100 kΩ, 1% ILIM resistor. Do not advertise this as a 500 mA port;
  its lower limit must be checked against the accessory and regulator budget.
  The fault output is available as a net but is not connected to host monitoring.
- The LCD uses SPI interface II and the shared host bus. Four separate 150 Ω
  resistors limit the backlight branches, with a common low-side switch. This
  deliberately gives reduced brightness; it is not a regulated 80 mA driver.
  The existing +5V_RF name now covers the LF frontend and backlight loads.
  LCD VCI/VDDI use +3V3: validate worst-case rail tolerance against the panel's
  operating limits before release. Final capacitor MPN/DC-bias checks remain.
- IR_RX moves from the keypad scanner to U1 pad 15 / GPIO3. Scanner pin 14
  becomes LCD_BL_EN. GPIO3 is a JTAG-selection strap; default ESP32 eFuses
  ignore it for that choice. Do not change that policy without a boot review.
- U20 targets 3.792 V with 374 kΩ / 100 kΩ feedback and forced PWM. Its input
  is VBAT, not VSYS. The 390 kΩ / 100 kΩ EN divider gives approximately
  3.92 V rising and 3.43 V falling UVLO, before tolerances. This conservative
  prototype choice can prevent modem startup on a partly discharged battery.
  Q3/Q4 force shutdown when SYS_EN is off. Burst capability, startup load,
  connector voltage drop and the exact modem supply range remain unvalidated.
- The modem itself remains on a detachable adapter. No SIM supply, codec,
  level translator or carrier-approved VoLTE implementation is claimed here.
  Selecting a regulator does not resolve that adapter.
- NFC RF pins and LF coil/timing nets intentionally remain unfinished. They
  have not been shorted to antennas or arbitrary capacitors to make ERC quiet.
- Case optics are purchased off-board parts: J24 pin 1 is LED anode via R48,
  pin 2 is its switched cathode. J25 is receiver OUT/GND/VS. There is no
  through-hole IR LED falsely represented by an 0805 LED footprint.
- Speaker connectors remain in the upper region; both microphone connections
  remain at the bottom. Do not connect the two differential speaker outputs
  together. Audio routing/selection and enclosure acoustics are unfinished.

## Relation to the 20 September review

| Review category | Handset Rev A status |
|---|---|
| Battery/charge/power | BQ25185 replaces the original TP4056 arrangement; switch controls enables. Protected pack, NTC installation, current budget, source policy and thermal tests remain release blockers. |
| Regulators | Exact ICs and inductor packages now exist. Local placement is only preparation for proper switching-current-loop routing and validation. |
| MCU/logic/keypad | Retains N16R8 PSRAM exclusions and corrected SPI pins; TCA8418 replaces PCF8574. Key routes retained. Firmware/interrupt budget remains open. |
| RF/comms | LoRa and CC1101 are bare ICs with incomplete RF/timing networks. Modem adapter, antenna isolation and VoLTE are unverified. |
| Sensors/peripherals | Real gauge, digital microphone, display, storage and IR circuits exist; end-to-end operation has not been tested. LF/NFC analog sections remain incomplete. |
| Passive/BOM | Inductor allowances replaced. Most resistors/capacitors still need orderable MPNs, voltage/power ratings and DC-bias review. The placed-parts CSV is not an approved purchasing BOM. |
| GPS/expansion | Real MAX-M10S and protected-port components exist. Routing, GNSS antenna performance and accessory tests remain incomplete. |
| Handset validation | Native schematic/PCB checks are rerun after this change. Passing connectivity assertions is not proof of circuit correctness. |
| Review/release | No Gerbers or manufacturing release issued. Original fabrication exports remain invalid for this redesign. |

Missing functionality before release: complete radio frontends; tuned NFC/LF
antennas; LF clock/reference/host input; modem adapter/SIM/audio/carrier support;
remaining routing; impedance stackup and ground planes; USB input protection;
power/thermal validation; complete purchased-part BOM; enclosure fit and
firmware bring-up for every peripheral.

## Primary references

- [ST ST25R3916B](https://www.st.com/resource/en/datasheet/st25r3916b.pdf), pin table and VFQFPN32 drawing.
- [Abracon ABM8](https://abracon.com/Resonators/abm8.pdf), crystal specification; fitted load caps are provisional until layout parasitics are measured.
- [TI TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf), pinout and current-limit design.
- [TI TPD4E05U06](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf), protection pinout.
- [TI SN74AHCT125](https://www.ti.com/lit/ds/symlink/sn74ahct125.pdf) and [SN74LVC1G17](https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf), LF logic levels.
- [Hirose DM3](https://www.hirose.com/product/document?clcode=CL0609-0033-6-00&documentid=D49662_en&documenttype=Catalog&lang=en&productname=DM3AT-SF-PEJ2M5&series=DM3), socket contacts/lands.
- [EastRising display](https://www.buydisplay.com/download/manual/ER-TFT024IPS-3_Datasheet.pdf), pages 9–11.
- [Hirose FH12](https://www.hirose.com/en/product/document?clcode=CL0586-0600-5-55&documentid=D31648_en&documenttype=Catalog&lang=en&productname=FH12-11S-0.5SH%2855%29&series=FH12), shared top/bottom-contact lands, distinct body envelopes. Custom top-contact footprint still needs independent inspection.
- [Vishay TSAL6400](https://www.vishay.com/docs/81011/tsal6400.pdf), [TSOP38438](https://www.vishay.com/docs/82491/tsop382.pdf), [AOS AO3400A](https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf).
- [TI TPS63070](https://www.ti.com/lit/ds/symlink/tps63070.pdf), including asymmetric RNM0015A power-pad geometry. Custom land/stencil needs independent inspection.
- [Coilcraft XFL4020](https://www.coilcraft.com/getmedia/50632d43-da1b-4cdb-8ab4-3029cab51df3/xfl4020.pdf), ratings and recommended lands.
- [ESP32-S3](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf), GPIO3 strap/eFuse behavior.
