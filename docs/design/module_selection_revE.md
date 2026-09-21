# OWASSO-1 module selection — rev E

This freezes the mechanical/interface targets used for the next PCB revision.
The named product variant must be purchased; generic marketplace clones are not
drop-in substitutes.

## Selected interfaces

| Function | Selected hardware | Mechanical/interface target | PCB action |
|---|---|---|---|
| LTE | SIMCom CC-MCore-A7670E-LASE audio carrier | 44.45 x 31.75 x 12.44 mm; two side headers, 12-pin + 11-pin, 2.54 mm; IPEX-1; micro-SIM | J1 uses the documented left-row/right-row order and exposes analog MIC/SPK plus UART/control |
| LoRa | Ai-Thinker Ra-01SH | 17 x 16 x 3.2 mm SMD-16 castellated module; SX1262 SPI; 803–930 MHz; up to 22 dBm; external antenna | Replace J3's Ebyte 22-pad footprint with the manufacturer Ra-01SH SMD-16 land pattern; reserve antenna matching and RF keepout |
| Display | Waveshare 3.5inch Capacitive Touch LCD, SKU 29318 | 61.00 x 92.44 mm; ST7796S SPI + FT6336U I2C; 18-pin 0.5 mm FPC | J7 is now mapped to the published 18-pin FPC signal assignment |
| Battery | MakerFocus 3.7 V 2000 mAh protected pouch | 50 x 34 x 10 mm ±2 mm; listing specifies Micro JST 1.25 plug | J13 changed away from PH 2.0; verify whether the purchased lead is JST-GH/PicoBlade-compatible before ordering PCB assembly |
| Trackball | Pimoroni PIM447 | 25 x 22 x 11 mm; 5-pin header; I2C address 0x0A/0x0B; INT output | J6 changed to 1x05 and mapped VCC/GND/SDA/SCL/INT |
| Call audio | A7670 analog voice path | MIC+, MIC−, SPK+, SPK−; electret microphone and 8-ohm speaker are separate enclosure parts | J12 is electrically mapped to J1 SC/SD/SR/SV |

## Display FPC mapping

The Waveshare 18-pin slot mapping is:

| FPC pin | Signal |
|---:|---|
| 1 | VCC |
| 2 | LCD_BL |
| 3 | GND |
| 4 | SCLK |
| 5 | MOSI |
| 6 | MISO |
| 7 | LCD_DC |
| 8 | LCD_RST |
| 9 | LCD_CS |
| 10 | SD_CS |
| 12 | TP_RST |
| 13 | TP_SCL |
| 14 | TP_SDA |
| 15 | TP_INT |
| 11, 16–18 | NC/reserved on the product table |

The current controlled netlist maps these to J7. Touch reset/interrupt are
exposed as `TP_RESET` and `TOUCH_INT`; `TOUCH_INT` still needs an ESP32 GPIO
assignment before release.

## Keypad

The project now has SW2–SW17 and D2–D17: sixteen compact KMR2 switches and
sixteen steering diodes in a 4-row × 4-column matrix. J11 is an optional 8-pin
external keypad harness: rows 1–4, then columns 1–4. The PCB source places the
switches on the front and diodes on B.Cu.

## Remaining fabrication blockers

1. Freeze the purchased CC-MCore-A7670E-LASE board revision and verify the
   header row center spacing against the custom J1 footprint before ordering.
2. Verify the Ra-01SH SMD-16 land pattern against the purchased module drawing
   before assembly. It is an SMT castellated module, not a normal 2.54 mm
   plug-in board. The manufacturer specifies 3.3 V operation and up to 140 mA
   working current for the standard Ra-01SH.
3. Assign an ESP32 GPIO to `TOUCH_INT` and add the missing display touch reset
   connection if touch is required.
4. Reroute the rebuilt 4x4 board and clear electrical DRC. The current board is
   intentionally a placement-only rebuild after changing the keypad/module
   interfaces.

## References

- Waveshare display/product pin table: https://www.waveshare.com/3.5inch-capacitive-touch-lcd.htm
- SIMCom A7670E-LASE core-board dimensions/interface summary: https://manuals.plus/ae/1005007419043953
- 23-pin 12+11 row order reference: https://www.arikporat.com/wp-content/uploads/2026/03/sending-sms-and-position-gps.pdf
- A7670E compact carrier 7-pin order: https://www.faranux.com/product/a7670e-4g-lte-cat1-core-board/
- Ai-Thinker Ra-01SH: https://docs.ai-thinker.com/Ra-01SH/index.html
- MakerFocus battery: https://www.makerfocus.com/products/makerfocus-3-7v-2000mah-lithium-rechargeable-battery-1s-3c-lipo-battery-with-protection-board-pack-of-4
- Pimoroni PIM447: https://wholesale.pimoroni.com/en-us/products/trackball-breakout
- Adafruit I2S microphone reference: https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/pinouts
