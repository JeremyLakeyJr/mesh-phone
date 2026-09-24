# Handset Rev A — PCB redesign in progress

Open [generated/handset.kicad_pro](generated/handset.kicad_pro) in KiCad 10.
This is a new board and hierarchical schematic, not the old Rev F layout.
**It is incomplete, partially routed, and not ready to fabricate or power.**
The original Rev F project is preserved in `../rev-f/`.

Latest: [SX1262 core regulator correction](sx1262-power-review.md).
The clock and RF frontend are still incomplete.

## Implemented in the design files

- 66 × 142 × 1.6 mm board with four copper layers, four 2.2 mm mounting
  holes and a 27 × 24 mm trackball opening. The extra 4 mm length prevents
  the mounting drills from breaking through the former 138 mm outline.
- Retained ESP32-S3-WROOM-1-N16R8; PSRAM pads 28–30 stay unconnected.
- A rebuilt system index and 21 functional schematic sheets, including
  GNSS/antennas, NFC, protection, storage/IR, LF support, display and modem power.
  See [schematic PDF](generated/handset-schematic.pdf) and
  [rebuild review](schematic-rebuild-review.md) for corrections and remaining work.
- Sixteen switches at the enclosure coordinates, TCA8418 scan circuit,
  matrix row traces on F.Cu and column traces on In2.Cu. Scanner fanout remains.
- BQ25186 programmable charger, TPS63802 3.3 V converter, TPS62840 1.8 V converter,
  TPS61023 LF/backlight 5 V converter and MAX17048 gauge circuits.
- Fused battery and USB paths, TPS25200 eFuse, TUSB320LAI Type-C detection,
  TLV704 always-on detector supply and TCA9536 charge controls. The 113-pad
  local power-entry cell passes copper continuity; firmware and external
  distribution are unfinished. See [power-entry-review.md](power-entry-review.md).
- Main 3.3 V converter local copper is routed and continuity-checked across
  U7, L1, C20–C22 and R30–R33. External power distribution remains incomplete;
  see [3v3-layout-review.md](3v3-layout-review.md).
- CC1101 clock, filtered supply and 868/915 MHz balun/matching/filter circuit
  are captured with specified parts and checked PCB placement. RF routing and
  tuning remain; see [cc1101-review.md](cc1101-review.md).
- SX1262 and HTRC110 footprints with host/control nets; their oscillator,
  RF matching and antenna circuits are not complete.
- MAX98357A media amplifier, SPH0645 digital mic, separate analog call-audio
  harnesses, native ESP32 USB-C and dedicated modem/expansion connectors.
- Manufacturer-derived custom pin definitions and TPS63802 DLA0010A land
  pattern. Custom library geometry still needs an independent pre-fab review.
- MAX-M10S GNSS; ST25R3916B NFC and oscillator; TPS2553 expansion current
  limiter and TPD4E05U06 protection arrays; Hirose DM3D-SF microSD socket;
  LF level translators; transistor-driven case-mounted IR; top-contact
  display connector/backlight switch; TPS63070 regulated modem supply.
- Named Coilcraft XFL4020 inductors replace the generic inductor allowances.
  Details and outstanding electrical work: [population-review.md](population-review.md).

The current component count, native ERC/DRC findings, remaining airwires and
schematic-to-board integrity results are in
[generated/verification-summary.json](generated/verification-summary.json).
The seven former reservation rectangles have been replaced by physical parts
and schematic circuits. Zero reservation rectangles does **not** mean that the
circuits are complete or that the PCB can be ordered.

## Critical unfinished work

| Block | Required work before release |
|---|---|
| GNSS | MAX-M10S is populated. Finish its RF feed, decoupling placement and coexistence review; no hardware backup supply is implemented. |
| Cellular | Select exact unlocked modem/firmware and establish calls, SMS and data on target carriers. The detachable adapter needs its own SIM, antenna feeds, voltage translation, regulated peak-current supply and audio implementation. |
| LCD / touch | ER-TFT024IPS-3 pinout and FH12A-50S-0.5SH(55) connector are captured with backlight switching. Confirm purchased CTP configuration, rail tolerances, FPC orientation/bending and firmware. |
| NFC | ST25R3916B, crystal and bypass components are populated. Finish and tune the antenna matching/receive network and validate oscillator loading. |
| Radio frontends | SX1262 core DC-DC support is captured; finish TCXO/PA/RF switch/matching and routing. Route and qualify the implemented CC1101 clock/decoupling/balun/filter circuit and separate antenna feed. |
| LF RFID | SN74AHCT125 and SN74LVC1G17 translation is populated. Clock, analog reference, coil network and timing-capable host return path remain incomplete. |
| GPIO budget | Confirm scanner GPIO behavior and LCD D/C throughput. IR_RX now uses ESP32 GPIO3; preserve default JTAG eFuse policy and verify boot behavior with active IR. |
| USB / J16 | TPS2553 and signal ESD arrays are captured. Finish protected routing, VBUS protection and power-off accessory policy; test current limit and ESD response. |
| Storage / IR | DM3D-SF and IR driver/harnesses are captured. Validate card access, TSAL6400/TSOP38438 case mounting and firmware. |
| Mechanical / RF | Check actual populated heights, display FPC bends, antenna keepouts, connector mating direction and trackball retention. Power-switch placement has moved and needs matching case access. |
| Layout | Finish placement, reference-plane design, all remaining routing, controlled impedance, thermal copper, ground stitching and silkscreen. Clear native ERC/DRC. |

## Power and connector contracts

J1 is a provisional two-pin battery connector; verify the purchased MakerFocus
pack polarity and plug before populating it. J2 is an external 10 kΩ B3435
thermistor to be thermally coupled to the battery; the two-wire pack itself does
not supply that signal. The BQ25186 CE input defaults off; firmware must apply
and read back [charger-policy.json](charger-policy.json) before charging.
The contract requests 300 mA charge on enumerated legacy USB or 500 mA on
qualified Type-C sources, subject to source and thermal limits. It is not yet
implemented firmware. Validate pack protection and discharge current; the
modem burst budget and powered-off charging remain unresolved.

SW19 controls converter enables. VSYS, charger, and battery gauge can remain
energized while the handset rails are off. Inductors now have exact XFL4020
MPNs and documented land patterns; rated-current and thermal review remains.
The legacy-named +5V_RF rail now also supplies the display backlight.

J16 preserves Rev F pin order: GND, EXP_3V3, SCL, SDA, SCK, MOSI, MISO, CS,
IRQ, GND. It is a locking JST GH cable port, independent of the modem.
U14 now supplies EXP_3V3 through a TPS2553 with a 100 kΩ limit resistor;
U15/U16 protect the seven signals. This is captured circuitry, still unrouted
and untested. Swap accessories with power off.

J8 is the proposed modem adapter's 3.3 V logic contract: GND, host TX, host RX,
LTE_ON, GND, MODEM_STATUS. Raw modem UART pins must not be connected unless
their voltage levels match; translation belongs on the adapter. J9 reserves a
separate regulated modem supply with two supply and two ground contacts.
U20 now generates nominal 3.792 V from VBAT, with hardware shutdown and
conservative battery UVLO; it does not connect the modem to raw charger SYS.
Startup requires a sufficiently charged battery (about 3.92 V nominal).
Connector/contact current, cable resistance and transient limits are not yet
validated. J4 carries adapter call speaker ± and microphone ±.
J7 is a proposed harness for PIM447, not a claim that its pad order matches it.

## Multi-carrier requirement

The user requires unlocked operation across carriers. A7672G is consequently
**a candidate, not a frozen or universally compatible modem**. Quectel EG25-G
is another research lead with broader published carrier documentation, but
carrier data approval does not establish smartphone VoLTE acceptance. No
universal-carrier claim is made, and no carrier-specific module is hard-wired
into this main board. The replaceable modem adapter preserves that choice.

## Reproduce and inspect

Edit the saved project directly. `scripts/build_handset_pcb.py` refuses to
overwrite an existing board. The additive population scripts are one-shot
migrations with snapshots/markers; do not rerun them to reset manual placement.

Run `bash scripts/check_handset_pcb.sh` for native XML
netlist export, ERC, DRC, integrity checks and SVG previews. Integrity checks verify real exported
schematic pin nets against board pads and mounting/key coordinates. Passing
them does not waive native errors or establish electrical functionality.

Run `python scripts/check_handset_release.py` for the separate release gate.
It intentionally fails while native errors, unrouted connections or engineering
blockers remain. See [population-review.md](population-review.md) for the
22 September checkpoint and remaining work by review category.

## Primary design references

- [TI BQ25186](https://www.ti.com/lit/ds/symlink/bq25186.pdf)
- [TI TPS63802, including DLA0010A land pattern](https://www.ti.com/lit/ds/symlink/tps63802.pdf)
- [TI TPS62840](https://www.ti.com/lit/ds/symlink/tps62840.pdf)
- [TI TPS61023](https://www.ti.com/lit/ds/symlink/tps61023.pdf)
- [TI TCA8418](https://www.ti.com/lit/ds/symlink/tca8418.pdf)
- [TI CC1101](https://www.ti.com/lit/ds/symlink/cc1101.pdf)
- [Analog Devices MAX17048](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf)
- [u-blox integration-document availability](https://content.u-blox.com/sites/default/files/documents/UBX-M10050-KB_IP_IN_UBX-22012688-2.pdf)
- [SIMCom A7672G specifications and certification list](https://www.simcom.com/product/A7672G.html)
- [Quectel EG25-G carrier and software documents](https://www.quectel.com/product/lte-eg25-g/)
