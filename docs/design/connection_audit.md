# Connection audit — 2026-09-13

This file records the researched electrical interfaces used by the corrected
controlled netlist. It is intentionally separate from routing status: a clean
route cannot make an incorrect module pinout correct.

## Corrected in source

### ESP32-S3-WROOM-1

The PCB footprint numbers are module pad numbers. They are not GPIO numbers.
The controlled netlist now maps the functions to actual WROOM-1 pads, including
native USB on module pads 13/14 (GPIO19/GPIO20), I2C on pads 39/38
(GPIO1/GPIO2), and the selected camera, SPI, radio, and UART assignments.

### PCF8574 keypad expander

| PCF8574 pin | Function |
|---:|---|
| 1–4 | KEY_R1–KEY_R4 (P0–P3) |
| 5–7, 9 | KEY_C1–KEY_C4 (P4–P7) |
| 8 | GND |
| 10–12 | GND (A0–A2 = address 0x20) |
| 13 | EXP_INT |
| 14 | I2C_SCL |
| 15 | I2C_SDA |
| 16 | 3V3 |

### Waveshare 3.5-inch 18-pin display FPC

The selected host interface uses pins 1, 2, 3, 4–10, and 12–15. Pins 11 and
16–18 are left unassigned rather than being tied to guessed signals.

### Molex 104031-0811 microSD

SPI mode is now mapped to the actual card contacts: pin 2 = CS, 3 = MOSI,
4 = 3V3, 5 = SCK, 6 = GND, 7 = MISO. Pins 1 and 8 (DAT2/DAT1) are unused;
the card-detect switch is exposed on 9/10 as SD_DET-to-GND.

## Still blocked from fabrication routing

### Camera

The project is now locked to a raw OV2640-style flex interface using the
documented ESP32-S3-EYE 24-pin ordering. J8 uses `CAM_2V8` for AVDD and DOVDD,
and `CAM_1V5` for DVDD. U9/U10 were added as ME6211C28M5G and ME6211C15M5G
regulators with input/output bulk capacitors. RESET has a 10 kΩ pull-up to
`CAM_2V8`; PWDN has a 10 kΩ pull-down to ground.

### 5 V boost rail

U8 is now TPS61023 in the SOT563 footprint: pin 1=FB, 2=EN, 3=VIN,
4=GND, 5=SW, and 6=VOUT. EN is tied high to VBAT, L1 is 1 µH from VBAT to
SW, and the feedback divider controls `MODEM_5V`. The old external SS14 was
removed because TPS61023 is synchronous. The inductor, capacitors, feedback
divider, current capability, and modem burst load still require final power
integrity review.

The source/netlist correction is complete. The regenerated PCB still needs a
placement cleanup around the new camera regulator cluster, followed by routing
and schematic regeneration. No Gerber release is valid yet.
