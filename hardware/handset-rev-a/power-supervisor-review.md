# Separate charging supervisor — circuit capture, 2026-09-25

User selected a separate low-power controller. The saved schematic and PCB now
capture that architecture; **powered-off charging is not yet functional or
qualified. DO NOT FABRICATE OR POWER.** The existing BQ25186 remains the battery
charger. STM32G031G8U6 manages its policy independently of the ESP32.

The following describes the initial supervisor capture. The subsequent
[charge-inhibit update](charge-inhibit-review.md) adds and routes Q8/R79 and U25
PA0 permission. Current totals: 238 components, 2,104 integrity checks, 118 local
power-entry pads. [Supervisor routing](supervisor-routing-review.md) now passes
physical continuity for 67 endpoints; target firmware and qualification remain.

## Implemented

- U25 STM32G031G8U6, 4 × 4 mm UFQFPN28, internal oscillator, local 100 nF +
  4.7 uF bypass, NRST pull-up/filter and five SWD service pads.
- U26 TPS7A0230PDBVR supplies PWR_AON_3V0 from VSYS upstream of SW19.
  Pins IN1/GND2/EN3/NC4/OUT5; EN follows VSYS. Both capacitors are 4.7 uF,
  GRM188R61E475KE11D, 0603 X5R 25 V. Effective capacitance still needs checking.
- U24, C60 and status pull-ups R66/R69 move from switched +3V3 to this rail.
- U25 PB8/PB7 (pins 28/27), I2C1 AF6, exclusively own U3 0x6A and U24 0x41
  through CHG_I2C_SCL/SDA, with 10k pull-ups. MAX17048 stays on the host bus.
- U27 TCA9800DGKR separates the switched host bus from the supervisor's I2C2.
  VCCA and EN use switched +3V3; VCCB uses PWR_AON_3V0. Its B-side current
  sources require **no external or MCU internal pull-ups** on PWR_HOST_SCL/SDA.
  A-side pull-ups remain on the existing host rail.
- U25 pins 18/19 need PA11/PA12 remapping and AF6 for I2C2. Host address 0x42
  is reserved here; neither the protocol nor its firmware is implemented.
- SW19 still disables the main rail. No ESP32 replacement. Existing placement
  and all 792 copper geometries are retained; only three local copper islands
  were reassigned to their new nets. New circuitry is placed, **unrouted**.

18 new parts bring the schematic to 236 components on 23 sheets. New BOM:
`generated/power-supervisor-bom.csv`. Schematic page: `power-supervisor.kicad_sch`.
SWD pad order TP2–TP6: AON reference, GND, SWDIO, SWCLK, NRST. VTREF is sense
only; debugger power must not feed this rail.

## Verification

Native netlist/PCB parity: zero differences. 2,087 integrity assertions pass.
38 independent pin contracts and five negative tests cover power domains,
private bus ownership and absence of B-side pull-ups. No added ERC/DRC findings:
30 existing ERC findings, four USB1 hole-clearance findings; 499 unconnected
items remain. Local power-entry continuity still passes for its 113 pads;
that does not establish continuity to the new supervisor.

## Required before enabling charging

- Regulator, bypass, ground, both buses and programming pads are now routed; check
  rise times, pull-up loading and regulator dropout across the battery range.
  Lower standby demand is a design intent, not a measured result. Include
  U3/U24/U27/NTC and pull-up currents in the total budget.
- Port the portable controller to STM32 with bounded I2C operations, independent
  watchdog, durable inhibit/fault history and an audited service rearm path.
  Enable BOR/reset protection and verify PA11/PA12 remapping against RM0444.
- **Qualify reset-time charge inhibit:** Q8/R79 now provide a separately routed
  PA0 permission, independent of retained U24 outputs. Verify gate discharge,
  /CE rise and current decay on reset/BOR/IWDG; implement the independent GPIO
  HAL. See charge-inhibit-review.md.
- Define a fail-closed host permission lease: legacy USB authorization expires
  on host shutdown/reset, link loss, USB detach/suspend/deconfiguration. U25
  has no USB device peripheral connection. With host off, legacy charging must
  stay disabled; autonomous Type-C charging requires qualified CC permission.
- Qualify VSYS startup with an empty/protected pack, regulator sequencing,
  TCA9800 powered-off leakage, unpowered host isolation and Type-C source
  recovery. Deeply depleted-pack recovery remains unimplemented.
- Verify the actual MakerFocus pack, protection/current limits, NTC attachment,
  thermal limits and modem burst budget; published dimensions are not a physical
  inspection. `exact_pack_qualified` must remain false until qualified.

The ESP-IDF direct charger adapter under `firmware/power/esp_idf` predates this
selection and is **not the driver for this PCB**. ESP32 must use the supervisor
protocol, not write U3/U24 directly. Host tests do not establish target firmware
or hardware behavior.

## Manufacturer references

- [ST STM32G031 datasheet](https://www.st.com/resource/en/datasheet/stm32g031g8.pdf):
  UFQFPN28 pin assignment, AF6 I2C mapping, decoupling and supply range.
- [TI TPS7A02 datasheet](https://www.ti.com/lit/ds/symlink/tps7a02.pdf):
  DBV pinout, 3.0 V PDBVR ordering option and capacitor requirements.
- [TI TCA9800 datasheet](https://www.ti.com/lit/ds/symlink/tca9800.pdf):
  dual supplies, powered-off behavior, EN reference and B-side pull-up exclusion.
- [Murata capacitor specification](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM188R61E475KE11-01A.pdf).
