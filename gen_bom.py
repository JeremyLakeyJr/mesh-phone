#!/usr/bin/env python3
"""Build final BOM CSV with LCSC part numbers, quantities, and price columns."""
import csv

rows = [
    # ref, description, MPN/package, qty, source, lcsc, unit_price_est
    ("U1", "ESP32-S3-WROOM-1-N16R8 MCU module", "ESP32-S3-WROOM-1-N16R8", 1, "LCSC", "C2913205", 4.50),
    ("U2", "I2C GPIO expander (keypad+trackball dirs)", "MCP23017T-E/SO SOIC-28", 1, "LCSC", "C32945", 1.20),
    ("U3", "Li-ion charger IC 1A", "TP4056 ESOP-8", 1, "LCSC", "C382139", 0.25),
    ("U4", "Battery protection IC", "DW01A SOT-23-6", 1, "LCSC", "C14213", 0.10),
    ("U5", "3.3V LDO 500mA", "ME6211C33M5G SOT-23-5", 1, "LCSC", "C82942", 0.15),
    ("U6", "Fuel gauge (header-mounted)", "MAX17048G+T10", 1, "LCSC", "C2681679", 1.80),
    ("J1", "LTE Cat-1 modem core board + SIM slot", "A7670SA-FASE core board", 1, "AliExpress", None, 14.00),
    ("J2", "Sub-GHz transceiver module 300-928MHz", "CC1101 N503 module", 1, "AliExpress", None, 4.00),
    ("J3", "LoRa SX1262 mesh module (Meshtastic/RNode)", "Ebyte E22-400M30S", 1, "cdebyte.com", None, 8.00),
    ("J4", "NFC reader/writer/emulator", "PN532 breakout red-board", 1, "AliExpress", None, 5.00),
    ("J5", "125kHz RFID reader", "RDM6300", 1, "AliExpress", None, 2.50),
    ("J6", "Scroll ball input", "BlackBerry trackball breakout", 1, "PMD Way/eBay", None, 8.00),
    ("J7", "Display 2in IPS 320x240 SPI", "ST7789V FPC module", 1, "AliExpress/Amazon", None, 6.00),
    ("J8", "Camera 2MP DVP retro", "OV2640 module w/ flex", 1, "AliExpress", None, 3.00),
    ("J9", "microSD push-push socket", "Molex 104031-0811", 1, "LCSC", "C114757", 0.45),
    ("J10", "SIM card connector", "push-type nano-SIM", 1, "LCSC/AliExpress", None, 0.60),
    ("SW1_9", "Keypad tactile switches low-profile x9", "SKRPACE010 / ALPS SKRP", 9, "LCSC", "C318884", 0.15),
    ("D_IR1", "IR emitter LED 940nm", "TSAL6200", 1, "LCSC", "C9962", 0.12),
    ("U7", "IR receiver 38kHz", "TSOP38238", 1, "LCSC", "C134616", 0.35),
    ("USB1", "USB-C receptacle 16pin", "GCT USB4105 or equiv", 1, "LCSC", "C165948", 0.55),
    ("SW_PWR", "Slide switch SPDT", "SS12D00 style", 1, "LCSC/AliExpress", None, 0.30),
    ("BT1", "Li-ion cell protected 18650 3500mAh", "Samsung 35E genuine", 1, "18650BatteryStore", None, 6.50),
    ("PCB", "Custom 4-layer PCB 62x128mm", "JLC04161H-7628 stackup", 5, "JLCPCB", None, 1.40),  # per-board econ
    ("ANT1", "LTE antenna u.FL + pigtail", "4G/LTE blade antenna", 1, "AliExpress", None, 2.00),
    ("ANT2", "LoRa/SubGHz antenna u.FL", "868/915MHz rubber duck", 1, "AliExpress", None, 2.50),
    ("PASS", "Passives kit: 0805 R/C, 1N4148W x9+, bulk caps 1000uF x2", "assorted", 1, "LCSC/JLC-PCBA", None, 3.00),
]

total_unit = sum(r[6]*r[3] for r in rows)
with open("/home/lakey/Documents/owasso1-pcb/bom_priced.csv","w",newline="") as f:
    w = csv.writer(f)
    w.writerow(["Refs","Description","MPN","Qty","Source","LCSC","UnitUSD","ExtUSD"])
    for ref,desc,mpn,qty,src,lcsc,unit in rows:
        w.writerow([ref,desc,mpn,qty,src,lcsc or "",f"{unit:.2f}",f"{unit*qty:.2f}"])
    w.writerow(["","","","","","TOTAL","", f"{total_unit:.2f}"])
print(f"Wrote bom_priced.csv — estimated unit BOM total: ${total_unit:.2f}")
