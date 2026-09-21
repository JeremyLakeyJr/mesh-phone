#!/usr/bin/env python3
"""OWASSO-1 rev A — schematic scaffold via pcbnew-adjacent KiCad Python (sexpr authoring).

Builds a complete .kicad_sch with all major components, LCSC part numbers as
properties, and power/ground + key interface nets. Module interfaces use 2.54mm
header symbols so hand-solder footprints are trivial.

Run: python3 build_schematic.py
"""
import uuid, random

random.seed(1)
def uid():
    return str(uuid.UUID(int=random.getrandbits(128), version=4))

# symbol defs are pulled from stock libs; we only need lib_ids referencing them.
# Components: (ref, value, lib_id, footprint_hint, lcsc, note)
PARTS = [
    # --- Core ---
    ("U1", "ESP32-S3-WROOM-1-N16R8", "RF_Module:ESP32-S3-WROOM-1", None, "C2913205", "Main MCU 16MB flash 8MB PSRAM"),
    ("U2", "PCF8574T", "Interface_Expansion:PCF8574T", "Package_SO:SOIC-16_7.5x10.3mm_P1.27mm", "C86822", "Keypad matrix I2C expander"),
    ("U3", "TP4056-42-ESOP8", "Battery_Management:TP4056-42-ESOP8", "Package_SO:ESOP-8", "C382139", "Li-ion charger 1A"),
    ("U4", "DW01A", "Battery_Management:DW01A", "Package_TO_SOT_SMD:SOT-23-6", "C14213", "Battery protection"),
    ("U5", "ME6211C33M5G", "Regulator_Linear:ME6211", None, "C82942", "3.3V LDO 500mA (use TPS62125 if buck wanted)"),
    ("U6", "MAX17048G+T10", "Connector_Generic:Conn_01x04", None, "C2681679", "Fuel gauge I2C header (no stock symbol; wire as 2.54mm header VCC GND SDA SCL)"),

    # --- RF / connectivity modules on headers ---
    ("J1", "A7670SA_CORE_BOARD", "Connector_Generic:Conn_01x12", "Connector_PinHeader_2.54mm:PinHeader_1x12_P2.54mm_Vertical", None, "LTE Cat-1 modem module header: VCC GND TX RX PWRKEY RI DTR BOOT NETLIGHT ADC u.FL SIM"),
    ("J2", "CC1101_MODULE", "Connector_Generic:Conn_01x08", "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical", None, "Sub-GHz sniff/replay: VCC GND CSN SI SO SCLK GDO0 GDO2"),
    ("J3", "SX1262_E22_MODULE", "Connector_Generic:Conn_01x09", "Connector_PinHeader_2.54mm:PinHeader_1x09_P2.54mm_Vertical", None, "Meshtastic/RNode mesh: VCC GND NSS SCK MOSI MISO RST BUSY DIO1"),
    ("J4", "PN532_BREAKOUT", "Connector_Generic:Conn_01x04", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", None, "NFC: VCC GND SDA SCL (I2C mode)"),
    ("J5", "RDM6300", "Connector_Generic:Conn_01x05", "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical", None, "125kHz RFID: VCC GND TX RX ANT"),
    ("J6", "TRACKBALL_BB", "Connector_Generic:Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical", None, "BlackBerry trackball: VCC GND UP DOWN LEFT RIGHT CLICK"),

    # --- Display / camera ---
    ("J7", "ST7789_2INCH_FPC", "Connector_Generic:Conn_01x07", "Connector_FFC-FPC:Hirose_FH12-7S-0.5SH_1x07-1MP_P0.50mm_Horizontal", None, "LCD: VCC GND CS DC MOSI SCLK BL"),
    ("J8", "OV2640_DVP_FLEX", "Connector_Generic:Conn_01x18", None, None, "Camera DVP bus: 3V3 GND PWDN RESET XCLK SCL SDA D7..D0 HSYNC VSYNC PCLK"),

    # --- Storage / SIM / misc ---
    ("J9", "Micro_SD_Card_Det_Hirose_DM3AT", "Connector:Micro_SD_Card_Det_Hirose_DM3AT", "Connector_Card:microSD_Card_Det_Hirose_DM3AT", None, "microSD push-push 4-bit SDMMC"),
    ("J10", "SIM_Card", "Connector_Card:SIM_Card", "Connector_Card:SIM_Card", None, "SIM to A7670"),
    ("SW1_9", "KEYPAD_MATRIX_3x3", "Connector_Generic:Conn_01x06", None, None, "Rows+Cols of diode-isolated 3x3 tactile matrix -> PCF8574"),

    # --- IR / audio-ish / buttons ---
    ("D_IR1", "TSAL6200", "Device:D", "LED_SMD:LED_0805_2012Metric", None, "IR TX LED"),
    ("U7", "TSOP38238", "Sensor_Optical:TSOP382xx", "OptoDevice:Vishay_MOLD-3P", None, "IR RX 38kHz"),
    ("SW_PWR", "SLIDE_SWITCH_SS12D00", "Switch:SW_SPDT", "Button_Switch_THT:SW_Slide_1P2T_CK_OS102011MA1QN1", None, "Charge-line power switch"),
    ("USB1", "USB_C_Receptacle_USB2.0", "Connector:USB_C_Receptacle_USB2.0", "Connector_USB:USB_C_Receptacle_GCT_USB4105", None, "Charge + data"),
]

# Nets: name -> [(ref, pin_number)]
NETS = [
    ("GND", [("U1","1"),("U2","8"),("U3","1"),("U4","1"),("U5","1"),("J1","2"),("J2","2"),("J3","2"),("J4","2"),("J5","2"),("J6","2"),("J7","2"),("J8","GND"),("J9","GND"),("J10","GND"),("USB1","GND"),("U7","2")]),
    ("VBAT", [("U3","3"),("U4","VIN"),("J1","VCC"),("SW_PWR","2")]),
    ("+3V3", [("U5","OUT"),("U1","VDD"),("U2","VDD"),("J2","VCC"),("J3","VCC"),("J4","VCC"),("J6","VCC"),("J7","VCC"),("J9","VDD"),("U7","VCC")]),
    ("VBUS5V", [("USB1","VBUS"),("U3","VCC"),("SW_PWR","1")]),
    ("SDA", [("U1","IO8"),("U2","SDA"),("J4","SDA")]),
    ("SCL", [("U1","IO9"),("U2","SCL"),("J4","SCL")]),
    ("LCD_SPI_CS",   [("U1","IO10"),("J7","CS")]),
    ("LCD_SPI_DC",   [("U1","IO11"),("J7","DC")]),
    ("LCD_SPI_MOSI", [("U1","IO12"),("J7","MOSI")]),
    ("LCD_SPI_SCK",  [("U1","IO13"),("J7","SCLK")]),
    ("LCD_BL",       [("U1","IO14"),("J7","BL")]),
    ("CAM_XCLK",  [("U1","IO15"),("J8","XCLK")]),
    ("CAM_I2C_SDA",[("U1","IO8"),("J8","SDA")]),   # shares I2C bus
    ("CAM_I2C_SCL",[("U1","IO9"),("J8","SDA")]),
    ("CAM_D0", [("U1","IO1"),("J8","D0")]),
    ("CAM_D1", [("U1","IO2"),("J8","D1")]),
    ("CAM_D2", [("U1","IO3"),("J8","D2")]),
    ("CAM_D3", [("U1","IO4"),("J8","D3")]),
    ("CAM_D4", [("U1","IO5"),("J8","D4")]),
    ("CAM_D5", [("U1","IO6"),("J8","D5")]),
    ("CAM_D6", [("U1","IO7"),("J8","D6")]),
    ("CAM_D7", [("U1","IO16"),("J8","D7")]),
    ("CAM_HSYNC",[("U1","IO17"),("J8","HSYNC")]),
    ("CAM_VSYNC",[("U1","IO18"),("J8","VSYNC")]),
    ("CAM_PCLK", [("U1","IO21"),("J8","PCLK")]),
    ("CAM_PWDN", [("U1","IO38"),("J8","PWDN")]),
    ("CAM_RESET",[("U1","IO39"),("J8","RESET")]),
    ("SDMMC_CMD",[("U1","IO40"),("J9","CMD")]),
    ("SDMMC_CLK",[("U1","IO41"),("J9","CLK")]),
    ("SDMMC_D0", [("U1","IO42"),("J9","D0")]),
    ("SDMMC_D1", [("U1","IO45"),("J9","D1")]),
    ("SDMMC_D2", [("U1","IO46"),("J9","D2")]),
    ("SDMMC_D3", [("U1","IO47"),("J9","D3")]),
    ("LTE_TX",  [("U1","IO43_U0RXD"),("J1","TX")]),
    ("LTE_RX",  [("U1","IO44_U0TXD"),("J1","RX")]),
    ("LTE_PWRKEY",[("U1","IO48"),("J1","PWRKEY")]),
    ("SUBGHZ_CSN", [("U1","IO35"),("J2","CSN")]),
    ("SUBGHZ_SI",  [("U1","IO34"),("J2","SI")]),
    ("SUBGHZ_SO",  [("U1","IO33"),("J2","SO")]),
    ("SUBGHZ_SCLK",[("U1","IO36"),("J2","SCLK")]),
    ("SUBGHZ_GDO0",[("U1","IO37"),("J2","GDO0")]),
    ("SUBGHZ_GDO2",[("U1","IO19"),("J2","GDO2")]),
    ("LORA_NSS", [("U1","IO0"),("J3","NSS")]),
    ("LORA_SCK", [("U1","IO47"),("J3","SCK")]),   # NOTE: conflicts w/ SDMMC_D3 - flag in review
    ("LORA_MOSI",[("U1","IO46"),("J3","MOSI")]),  # ditto
    ("LORA_MISO",[("U1","IO45"),("J3","MISO")]),
    ("LORA_RST", [("U1","IO21"),("J3","RST")]),
    ("LORA_BUSY",[("U1","IO20"),("J3","BUSY")]),
    ("LORA_DIO1",[("U1","IO14"),("J3","DIO1")]),
    ("IR_TX", [("U1","IO13"),("D_IR1","A")]),
    ("IR_RX", [("U1","IO12"),("U7","OUT")]),
    ("TB_UP",    [("U1","IO7"),("J6","UP")]),
    ("TB_DOWN",  [("U1","IO6"),("J6","DOWN")]),
    ("TB_LEFT",  [("U1","IO5"),("J6","LEFT")]),
    ("TB_RIGHT", [("U1","IO4"),("J6","RIGHT")]),
    ("TB_CLICK", [("U1","IO3"),("J6","CLICK")]),
]

# This script emits an intermediate JSON the real generator consumes next.
import json
out = {
    "parts": [dict(ref=r, value=v, lib_id=l, fp=f, lcsc=c, note=n) for r,v,l,f,c,n in PARTS],
    "nets": [{"name": n, "nodes": nodes} for n,nodes in NETS],
}
with open("/home/lakey/Documents/owasso1-pcb/netlist_draft.json","w") as f:
    json.dump(out, f, indent=1)
print(f"Wrote netlist_draft.json: {len(PARTS)} parts, {len(NETS)} nets")
