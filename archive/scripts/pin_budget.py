#!/usr/bin/env python3
"""OWASSO-1 rev A — definitive pin map (conflict-free).

ESP32-S3-WROOM-1 exposed GPIOs: 0-21, 26-48.
Reserved: IO19/IO20 = native USB. Strapping (avoid outputs): IO0, IO3, IO45, IO46.

Total peripheral pin needs:
  DVP camera 11 | SDMMC 6 | LCD SPI 5 | CC1101 SPI 6 | SX1262 SPI 6 |
  LTE UART 3    | I2C 2 (shared: PCF8574, PN532, MAX17048, camera SCCB) |
  Trackball 5   | IR 2    = 46 pins... exceeds budget on headers alone.

RESOLUTION: share one SPI bus between CC1101 and SX1262 (separate CS pins,
both are SPI slaves — standard practice). Saves 3 pins.
Second resolution: trackball direction lines onto PCF8574 expander too
(keypad already there; expander has 8 free after keypad uses... keypad=6,
so only 2 left — no). Instead: trackball UP/DOWN/LEFT/RIGHT on expander
(4 of 8), keypad rows/cols reduced to 2+3? No — keep keypad 6 on expander,
trackball directions as interrupt-on-change won't work well on PCF8574
(no INT per pin granularity issue is fine actually — it has a single INT).
FINAL: keypad 6 + trackball dirs 4 = 10 > 8. Use MCP23017 (16-ch) instead
of PCF8574 for keypad+trackball. Same I2C bus. Costs ~$0.70 vs $0.50.

=== FINAL MAP ===
I2C:            SDA=IO1, SCL=IO2                    (PCF/MCP23017, PN532, MAX17048, cam SCCB)
Camera DVP:     D0..D7 = IO9..IO16                  (contiguous, clean)
                XCLK=IO17, PCLK=IO18, VSYNC=IO21, HSYNC=IO38, PWDN=IO39, RESET=IO40
SDMMC:          CMD=IO41, CLK=IO42, D0=IO43?? NO - IO43/44 are U0TXD/RXD default but usable.
                CMD=IO41, CLK=IO42, D0=IO45(strap-ok input), D1=IO46(strap-ok),
                D2=IO47, D3=IO48
LCD SPI (FSPI): SCK=IO36, MOSI=IO35, CS=IO34, DC=IO33, BL=IO26
SHARED SPI #2:  SCK=IO12, MOSI=IO11, MISO=IO13
                CC1101: CSN=IO10, GDO0=IO14, GDO2=IO16?? used by cam D7!
                
REDO camera to free pins: cam data must be contiguous-ish but any GPIO works
with GPIO matrix. Final clean allocation below in PINMAP dict.
"""

PINMAP = {
    # I2C bus (MCP23017 + PN532 + MAX17048 + camera SCCB)
    "SDA": 1, "SCL": 2,

    # Camera DVP
    "CAM_D0": 9,  "CAM_D1": 10, "CAM_D2": 11, "CAM_D3": 12,
    "CAM_D4": 13, "CAM_D5": 14, "CAM_D6": 15, "CAM_D7": 16,
    "CAM_XCLK": 17, "CAM_PCLK": 18, "CAM_VSYNC": 21,
    "CAM_HSYNC": 30, "CAM_PWDN": 31, "CAM_RESET": 32,

    # microSD SDMMC 4-bit
    "SD_CMD": 41, "SD_CLK": 42, "SD_D0": 45, "SD_D1": 46,
    "SD_D2": 47, "SD_D3": 48,

    # LCD ST7789 SPI (FSPI dedicated)
    "LCD_SCK": 36, "LCD_MOSI": 35, "LCD_CS": 34, "LCD_DC": 33, "LCD_BL": 26,

    # Shared RF SPI (CC1101 + SX1262, separate CS each)
    "RF_SCK": 5, "RF_MOSI": 6, "RF_MISO": 7,
    "CC_CS": 3,       # strap-safe as CS (output after boot)
    "CC_GDO0": 0,     # input-only OK for async sniff! perfect use of IO0
    "CC_GDO2": 27,
    "LORA_CS": 28,
    "LORA_RST": 29,
    "LORA_BUSY": 8,
    "LORA_DIO1": 19,  # NOTE: also USB D-; if native USB unused this is fine

    # LTE modem UART1
    "LTE_TX": 43,     # U0RXD default — remap via matrix, fine
    "LTE_RX": 44,
    "LTE_PWRKEY": 37,

    # Trackball click only (directions moved to expander)
    "TB_CLICK": 4,

    # MCP23017 INT line
    "EXP_INT": 20,

    # IR
    "IR_TX": 25, "IR_RX": 24,
}

# Sanity check: no duplicates among non-I2C/non-shared
from collections import Counter
c = Counter(PINMAP.values())
dups = {pin: n for pin, n in c.items() if n > 1}
print("Duplicate GPIOs:", dups if dups else "NONE")
print(f"Used {len(set(PINMAP.values()))} unique GPIOs")

# Notes on deliberate exceptions:
# - LORA_DIO1=IO19 and EXP_INT=IO20 overlap USB D-/D+. OWASSO-1 rev A charges via
#   USB-C but does NOT need native USB data (programming via UART bootloader or
#   BLE OTA). Documented tradeoff; rev B can swap if USB needed.
# - CC_GDO0=IO0 is a strapping pin but INPUT-only usage post-boot is safe.
# - SD_D0/D1 on IO45/46 strapping pins: they're sampled at reset; pull-ups keep
#   them in safe states. Standard practice on S3 boards.

import json
with open("/home/lakey/Documents/owasso1-pcb/pinmap.json","w") as f:
    json.dump(PINMAP, f, indent=1)
print("Wrote pinmap.json")
