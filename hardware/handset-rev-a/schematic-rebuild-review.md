# Schematic rebuild — 24 September 2026

Later checkpoint: the [CC1101 circuit completion](cc1101-review.md) supersedes
the CC1101 missing-circuit entry and numerical counts in this rebuild snapshot.

All active schematic sheets have been rebuilt into a system index and 21
functional sheets. The 192-component population, ESP32-S3-N16R8, external
display, radio interfaces, top speaker/bottom microphone and expansion
connector are retained. This is an engineering draft, not a completed or
fabrication-ready electrical design.

Open [the schematic PDF](generated/handset-schematic.pdf) or
[the KiCad project](generated/handset.kicad_pro). The previous project is
snapshotted under `archive/handset-before-schematic-rebuild/`; the exact
snapshot and source hashes are in
[schematic-rebuild.json](generated/schematic-rebuild.json).

## Changes with electrical significance

| Reference | Correction | Basis |
|---|---|---|
| U4.1 | SX1262 VDD_IN connects to +3V3, separate from VREG | Semtech AN1200.40 SX1262 reference PA supply |
| U9.5 | HTRC110 MODE connects to ground for a short local interface | NXP HTRC110 application circuit |
| D1 | Unidirectional cathode/anode symbol replaces bidirectional TVS depiction; cathode remains USB_FUSED | Diotec SMF5.0A |
| U8.6 | MAX17048 QSTRT is an input tied to ground when unused | Analog Devices pin description |
| U6.17 | MAX98357A exposed ground pad is represented as a power input | Grounded exposed-pad connection |
| U20.8 | Internally paralleled VOUT terminal is passive; pin 7 retains the output-driver type | TPS63070 pin definition; both remain MODEM_SUPPLY |

Only U4.1 and U9.5 change PCB pad nets. Symbol electrical types were corrected
to describe the selected devices; unfinished radio inputs were not marked NC
or retyped to suppress their errors. Power flags identify actual external USB
and protected-pack sources through passive fuses and their ground return.
They do not assert that power distribution has been routed or qualified.

The charger, MCU boot/reset and main 3.3 V sheets now show explicit circuit
wiring; the keypad has a drawn 4 × 4 matrix. Other sheets group actual parts,
shared bypass banks and named interfaces. The display connector has a shared
ground bus. Those presentation changes do not complete missing RF networks.

## Verification

- All 192 parts appear exactly once. Exported KiCad pin nets match the design
  manifest, including individually isolated no-connect pins.
- 1,825 schematic/PCB integrity assertions pass; native schematic/PCB parity
  has zero findings.
- All 196 physical footprints, including four mounting holes, retain their
  positions, orientation, package, values and pad geometry. All 792 existing
  copper items retain their UUIDs, geometry and nets.
- Local power-entry continuity passes for 113 pads; main 3.3 V continuity
  passes for 26 pads. External distribution is excluded from these local tests.
- The charger register contract and five unsafe-policy negative tests pass.
  This is not implemented or tested charger firmware.
- Native ERC retains 37 findings: 31 isolated labels and six undriven inputs.
  Native DRC retains four USB connector internal hole-clearance findings and
  445 unconnected items. The extra airwire relative to the power-entry
  checkpoint follows the intentional pin-net corrections, not removed copper.

No ERC/DRC exclusions were added. The release gate stays closed.

## Electrical work still required

| Circuit | Missing implementation or qualification |
|---|---|
| SX1262 | 32 MHz clock, DCC/VREG power components, PA/RX matching, RF switch and 50-ohm feed. Freeze one manufacturer reference BOM and stackup. |
| CC1101 | 26 MHz crystal and load network, differential-to-single-ended matching/filter and antenna feed; resolve optional GDO2 handling. |
| HTRC110 | Oscillator, QGND/CEXT bypass, coil resonance/receive network, and a timing-capable host path. Expander-driven control is not evidence of working LF read/write timing. |
| NFC | Case-loop impedance, TX matching, receive divider/network and assembled-case tuning. |
| Host interfaces | Resolve RFID_DOUT_3V3, TRACKBALL_INT and MODEM_STATUS endpoints without breaking the ESP32 boot/PSRAM constraints. |
| Battery / USB | Implement charger firmware and fault handling; verify the actual pack and NTC. Powered-off charging, legacy-source recovery and modem burst-current budget remain open. |
| Other supplies | Finish auxiliary and modem converter layout; qualify effective capacitance, current, stability and thermal limits. |
| Cellular | Implement the actual replaceable modem adapter, SIM/RF/audio/logic translation and carrier-specific VoLTE qualification. |
| Display / peripherals | Verify purchased display/touch FPC option, firmware and all connector polarities; finish storage, IR, GNSS and protected expansion routing. |
| Release | Finish all routing and antenna coexistence work; independently review symbols, footprints, exact passive BOM and mechanical fit. |

The next electrical completion work is the radio frontends and LF host timing
allocation. A tidy schematic or a reduced ERC count is not a substitute for
those circuits.

## Manufacturer references

- [Semtech SX1262 reference-design entry](https://www.semtech.com/products/wireless-rf/lora-connect/sx1262mb2cas)
- [Semtech AN1200.40, manufacturer-authored distributor copy](https://cdn-reichelt.de/documents/datenblatt/A200/SX1262REFERENCE.pdf)
- [NXP HTRC110](https://www.nxp.com/docs/en/data-sheet/037031.pdf)
- [Analog Devices MAX17048/MAX17049](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf)
- [Analog Devices MAX98357A/MAX98357B](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf)
- [TI TPS63070](https://www.ti.com/lit/ds/symlink/tps63070.pdf)
- [Diotec SMF5.0A](https://diotec.com/files/diotec/productfiles/datasheet/smf50a.pdf)
- [TI CC1101](https://www.ti.com/lit/ds/symlink/cc1101.pdf)
- Power-entry component references and limitations: [power-entry-review.md](power-entry-review.md).
