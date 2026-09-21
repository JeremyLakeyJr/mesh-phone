# Revision F interface contract — engineering, not released

Open `mesh-phone.kicad_pro` in this directory. It is a separate engineering revision;
the original project is in `../main/`. See the electrical review in
`../../docs/reviews/review-2026-09-20/CONNECTION_REVIEW.md` before powering or ordering anything.

## Rear module port J16

Back-side vertical JST GH **BM10B-GHS-TBT(LF)(SN)**, 1.25 mm pitch, ten positions.
Mating cable housing: **GHR-10V-S**, using matching JST GH contacts. This is a
locking cable connection to interchangeable rear modules, not a blind-mating
card-edge dock. A recessed access port, blank and removable cable-connected pod are modeled in
`../../mechanical/enclosure/`; populated-hardware fit remains to be verified.

| Pin | Signal | Module contract |
|---:|---|---|
| 1 | GND | Ground |
| 2 | EXP_3V3 | Host-supplied 3.3 V; 50 mA usable module budget pending supply redesign |
| 3 | EXP_SCL | Shared I²C clock; 3.3 V open-drain |
| 4 | EXP_SDA | Shared I²C data; 3.3 V open-drain |
| 5 | EXP_SCK | Shared SPI clock, GPIO12 |
| 6 | EXP_MOSI | Host → module, GPIO13 |
| 7 | EXP_MISO | Module → host, GPIO14; high impedance when not selected |
| 8 | EXP_CS_PORT | Active-low module select, GPIO7; host 10 kΩ pull-up |
| 9 | EXP_IRQ_PORT | Module interrupt to GPIO15; use open-drain, host 10 kΩ pull-up |
| 10 | GND | Ground |

Pin numbers are connector pad numbers, **not an unverified left-to-right view of
the mating cable**. Check continuity against pin 1 before plugging a module in.

U10 is TPS2553DBVR with R14 = 232 kΩ, 1%, setting a low current-limit threshold
per its datasheet. The 50 mA interface budget is deliberately below the nominal
limit and is not a measurement of the unfinished host supply. C8/C9 provide
input/output bypassing. R15–R21 are 33 Ω series resistors on signal lines.

Power off and unplug USB before connecting/disconnecting a module. Do not
hot-swap. Do not supply power into this connector, use 5 V logic, or back-power
signals from a separate module supply. Do not connect raw VBAT. This port has
not been certified for externally exposed ESD events or arbitrary cable lengths.

Start SPI at 1 MHz and I²C at 100 kHz; validate faster speeds with the actual
cable and module. Keep the module cable short (target ≤50 mm). Existing I²C
targets include the PCF8574 at 0x20 and the display touch controller at 0x38;
reserve module addresses after scanning the populated host. An expansion module
must not add strong pull-ups that over-load the shared bus.

## GPS U9 and J15

- Receiver: **u-blox MAX-M10S-00B-01**, placed on B.Cu.
- U9 TXD pin 2 → R7 → ESP32 GPIO5, module pad 5 (host receive).
- ESP32 GPIO4, module pad 4 → R6 → U9 RXD pin 3 (host transmit).
- U9 TIMEPULSE pin 4 → GPIO6, module pad 6. Do not pull PPS low during startup.
- U9 VCC pin 8 and V_IO pin 7 → 3V3, with C5/C6 bypassing.
- V_BCKP, VIO_SEL, SAFEBOOT, EXTINT, RESET, I²C and VCC_RF unused/open by design.
- J15: U.FL-R-SMT-1(10), **passive GNSS antenna only**, no antenna DC bias.
- Proposed antenna: **Taoglas FXP611.07.0092C** flexible passive GNSS antenna,
  using its U.FL-compatible coax connection. Check the manufacturer's mounting
  recommendations against the final plastic housing, battery, display and RF
  antennas; do not stick it directly onto the battery or a ground plane.

The initial UART setting is 38400 baud, 8-N-1; use the selected receiver's
firmware documentation for its NMEA/UBX configuration. No GPS firmware or
acquisition test is included in this PCB-only repository. Absence of a backup
supply means loss of retained time/ephemeris when the phone powers off.

RF routing is only a connectivity candidate until its 50 Ω geometry is checked
against the actual fabrication stackup and antenna coexistence is tested.

## Changed MCU allocation

| Function | ESP32 GPIO | WROOM pad |
|---|---:|---:|
| GPS TX from host | 4 | 4 |
| GPS RX into host | 5 | 5 |
| GPS PPS | 6 | 6 |
| Expansion CS | 7 | 7 |
| Expansion IRQ | 15 | 8 |
| LCD reset | 16 | 9 |
| Touch reset | 17 | 10 |
| Touch interrupt | 8 | 12 |
| Shared SPI SCK | 12 | 20 |
| Shared SPI MOSI | 13 | 21 |
| Shared SPI MISO | 14 | 22 |
| LoRa CS | 21 | 23 |
| CC1101 CS | 47 | 24 |
| CC1101 GDO0 | 48 | 25 |
| BOOT button | 0 | 27 |

Pads 28/29/30 (GPIO35/36/37) are intentionally not used externally because this
design specifies the N16R8 module. This table supersedes the old top-level
`../../docs/design/gpio_table.md` for these signals only. Remaining one-pin interface nets are
listed in the electrical review and are not working features yet.
