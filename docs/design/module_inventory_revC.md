# OWASSO-1 module inventory and mechanical audit — rev E

This is the controlled module list extracted from:

- `/home/lakey/diy-phone-blueprint.html`
- `/home/lakey/diy-phone-build.html`
- `/home/lakey/diy-phone-sourcing.html`

The PCB is now 70 x 154 mm. A listed item is marked **on-board** only when its
actual connector or IC footprint is on the PCB. Large breakout boards are
external modules connected through a deliberate header/FPC interface; their
full body must not be silently treated as PCB copper.

| Requirement | PCB ref/interface | Selected part or interface | Mechanical basis | Status |
|---|---|---|---|---|
| MCU + Wi-Fi/BLE + PSRAM | U1 | ESP32-S3-WROOM-1-N16R8 | 18 x 25.5 mm module; antenna keepout required | on-board, placed |
| Camera | J8 | Hirose FH12-24S-0.5SH FPC | 0.5 mm pitch, 24 position, approx. 16.1 x 6.4 x 2.0 mm connector | on-board connector, placed |
| Display | J7 | Waveshare 3.5inch Capacitive Touch LCD 18-pin FPC interface | 0.5 mm FPC; vendor-specific 18-pin pinout; use matching panel/cable only | interface must be changed to vendor pinout before fab |
| Display module | external | Waveshare 3.5inch Capacitive Touch LCD, ST7796-class | 61.00 x 92.44 mm module; 320×480; 18-pin FPC option; touch signals included | selected panel family; freeze exact revision/cable |
| microSD | J9 | Molex 104031-0811 | about 11.95 x 11.40 x 1.42 mm | on-board, exact footprint selected |
| LTE modem | J1 | SIMCom CC-MCore-A7670E-LASE audio core carrier | 44.45 x 31.75 x 12.44 mm; 12-pin + 11-pin 2.54 mm side headers; IPEX-1; micro-SIM | custom J1 footprint and documented 23-pin audio/UART mapping |
| nano-SIM | J10 | JAE SF72S006 | 11.2 x 14.35 x 1.25 mm | on-board, placed |
| CC1101 | J2 | N503-style module header | N503 module about 17 x 16 x 3 mm | external module interface |
| SX1262 / LoRa | J3 | Ebyte E22-400M30S | 24 x 38.5 mm; SMT/castellated module; SPI; 30 dBm; antenna edge/keepout required | do not call current 9-pin J3 direct-fit; use module carrier/adapter |
| PN532 NFC | J4 | 4-pin UART/I2C module header | common breakout about 40 x 40 x 4 mm | external module interface; antenna not on PCB |
| RDM6300 LF RFID | J5 | 4-pin UART/power header | common board about 38 x 22 x 8 mm; 5 V module | direct VCC/GND/TX/RX interface; corrected from 5 pins |
| IR transmitter | D1 | TSAL6200 | 5 mm THT/LED envelope | on-board, placed |
| IR receiver | U7 | TSOP38238 | small 3-pin receiver envelope | on-board, placed |
| Trackball | J6 | Pimoroni PIM447 Trackball Breakout | 25 x 22 x 11 mm; 5-pin header: VCC, GND, SDA, SCL, INT; I2C 0x0A/0x0B | exact module selected; J6 changed to 5-pin |
| Keypad | SW2–SW17/D2–D17/U2 | 4 x 4 switch matrix + PCF8574 | compact KMR2 SMD tactiles; 16 switches + 16 steering diodes | implemented in source/netlist; PCB rebuilt with 4x4 placement |
| Audio | J12 | A7670 analog voice audio | MIC+, MIC−, SPK+, SPK−; use electret mic + 8-ohm speaker | mapped through J1 SC/SD/SR/SV on the 23-pin carrier |
| Battery | J13 | MakerFocus 3.7 V 2000 mAh protected pouch | 50 x 34 x 10 mm ±2 mm; listed with Micro JST 1.25 plug | PH 2.0 was wrong; J13 changed to 1.25 mm mating footprint |
| Charger/protection | U3/U4 | TP4056 + DW01A/FS8205A | power circuit needs complete protection FETs/passives | incomplete schematic/power section |
| Modem boost | U8/L1/D11/C1/R2/R3 | MT3608-class 5 V boost | required by the HTML power plan for modem peaks | PCB implementation added |
| USB-C | USB1 | GCT USB4105-xx-A | connector body/layout per GCT drawing | on-board, placed |
| Power switch | SW1 | CK OS102011MA1Q | side-access switch envelope | on-board, placement still collides |

## Mechanical conclusions

1. The 40 x 40 mm PN532, 38 x 22 mm RDM6300, 24 x 38.5 mm E22 module,
   trackball breakout, and LTE carrier cannot all be physically stacked inside
   a 56 x 122 mm PCB envelope. They must be external/front-panel modules or
   the phone must grow substantially.
2. The PCB therefore carries interfaces, power, protection, antenna keepouts,
   and the MCU/display/camera/card connectors. It does not claim full-board
   placement for those external modules.
3. J1 now targets the larger 23-pin audio carrier. Its left row is SC, SD, SR,
   SV, STA, TXD, RXD, RTS, PEN, R/P, GND, P/G; its right row is VEXT, VTTL,
   CTS, RI, DTR, RXD2, TXD2, VBAT, NET, VIN, VIN.
4. The 4x4 rebuild is a new placement-only candidate and must be rerouted and
   DRC-cleaned before fabrication.
5. The TP4056/DW01A/FS8205A protection network is represented, but its exact
   purchased implementation and battery connector variant still need a bench
   validation before production release.

## Sources used for dimensions

- ESP32-S3-WROOM-1: https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf
- Ebyte E22-400M30S: https://www.ebyte.com/product/452.html
- MakerFocus 2000 mAh pouch: https://www.makerfocus.com/products/makerfocus-3-7v-2000mah-lithium-rechargeable-battery-1s-3c-lipo-battery-with-protection-board-pack-of-4
- Molex 104031-0811: https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/104/104031/PS-104031-001-001.pdf
- Hirose FH12-24S: https://www.hirose.com/product/p/CL0586-0521-0-55
- JAE SF72: https://www.jae.com/en/connectors/series/detail/id%3D64200
- Ebyte/CC1101 and trackball dimensions: https://www.coralradio.com/CC1101.html and https://thepihut.com/products/trackball-breakout
- A7670SA-FASE carrier dimensions: https://manuals.plus/ae/1005005674566670
- A7670E-LASE compact 7-pin header and pin order: https://www.faranux.com/product/a7670e-4g-lte-cat1-core-board/
- E22-400M30S dimensions and pin definition: https://datasheet.lcsc.com/lcsc/1912111437_Chengdu-Ebyte-Elec-Tech-E22-400M30S_C411292.pdf
- PN532 breakout dimensions: https://www.espboards.dev/sensors/pn532/
- RDM6300 pinout and dimensions: https://www.espboards.dev/sensors/rdm6300/
- 3.5-inch 320×480 FPC display dimensions/interface: https://www.buydisplay.com/download/manual/ER-TFT035IPS-6_Datasheet.pdf
- RDM6300: https://www.espboards.dev/sensors/rdm6300/
- SIMCom A7670E-LASE 23-pin core board: https://manuals.plus/ae/1005007419043953
- A7670E compact 7-pin header order: https://www.faranux.com/product/a7670e-4g-lte-cat1-core-board/
- Waveshare 3.5-inch display: https://www.waveshare.com/wiki/3.5inch_Capacitive_Touch_LCD
- Pimoroni PIM447 trackball: https://wholesale.pimoroni.com/en-us/products/trackball-breakout
- Adafruit I2S microphone pinout reference: https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/pinouts
