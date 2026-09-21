#!/usr/bin/env python3
"""Add the missing power, battery, and real keypad parts to the design netlist."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
data = json.loads((root / "netlist_draft.json").read_text())
parts = {p["ref"]: p for p in data["parts"]}
nets = {n["name"]: n["nodes"] for n in data["nets"]}
nodes = nets

def add_part(ref, value, fp):
    if ref not in parts:
        parts[ref] = {"ref": ref, "value": value, "fp": fp}

def add_node(net, ref, pin):
    nodes.setdefault(net, [])
    item = [ref, str(pin)]
    if item not in nodes[net]:
        nodes[net].append(item)

def remove_node(net, ref, pin):
    if net in nodes:
        nodes[net] = [n for n in nodes[net] if n != [ref, str(pin)]]

def remove_ref(ref):
    for net in list(nodes):
        nodes[net] = [n for n in nodes[net] if n[0] != ref]
        if not nodes[net]:
            nodes.pop(net)

# Concrete power hardware required by the HTML build plan.
add_part("J13", "LiPo-BATTERY-MICRO-JST-1.25", "Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal")
parts["J13"] = {"ref": "J13", "value": "LiPo-BATTERY-MICRO-JST-1.25",
                 "fp": "Connector_JST:JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal"}
add_part("U8", "TPS61023DRLR-5V-BOOST", "Package_TO_SOT_SMD:SOT-563")
add_part("L1", "1uH-BOOST-INDUCTOR", "Inductor_SMD:L_1210_3225Metric")
parts["U8"] = {"ref": "U8", "value": "TPS61023DRLR-5V-BOOST",
                "fp": "Package_TO_SOT_SMD:SOT-563"}
parts["L1"] = {"ref": "L1", "value": "1uH-BOOST-INDUCTOR",
                "fp": "Inductor_SMD:L_1210_3225Metric"}
# TPS61023 is synchronous; the former external SS14 was both unnecessary and
# a reference collision with the keypad diode bank. Remove it completely.
parts.pop("D18", None)
remove_ref("D18")
for ref, value in [("C1", "1000uF-MODEM-BULK"), ("C2", "100uF-VBAT-BULK"),
                   ("C3", "10uF-3V3-BULK"), ("C4", "10uF-USB-IN")]:
    add_part(ref, value, "Capacitor_SMD:C_1206_3216Metric")
for ref, value in [("R1", "1.2k-TP4056-PROG"), ("R2", "180k-BOOST-FB"),
                   ("R3", "27k-BOOST-FB"), ("R4", "5.1k-USB-C-CC1-Rd"),
                   ("R5", "5.1k-USB-C-CC2-Rd"),
                   ("R6", "10k-CAM-RESET-PULLUP"),
                   ("R7", "10k-CAM-PWDN-PULLDOWN")]:
    add_part(ref, value, "Resistor_SMD:R_0805_2012Metric")
add_part("Q1", "FS8205A-PROTECTION-FET", "Package_TO_SOT_SMD:SOT-23-6")
add_part("U9", "ME6211C28M5G-CAM-2V8", "Package_TO_SOT_SMD:SOT-23-5")
add_part("U10", "ME6211C15M5G-CAM-1V5", "Package_TO_SOT_SMD:SOT-23-5")
for ref, value in [("C5", "10uF-CAM-2V8-IN"), ("C6", "10uF-CAM-2V8-OUT"),
                   ("C7", "10uF-CAM-1V5-IN"), ("C8", "10uF-CAM-1V5-OUT")]:
    add_part(ref, value, "Capacitor_SMD:C_1206_3216Metric")

# Freeze the selected external connector interfaces instead of inheriting the
# old generic-header mappings.  These are the published Waveshare 18-pin FPC
# and Pimoroni PIM447 5-pin trackball interfaces.
parts["J6"] = {"ref": "J6", "value": "Pimoroni-PIM447-Trackball",
                "fp": "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical"}
parts["J1"] = {"ref": "J1", "value": "A7670E-LASE-23P-12+11",
                "fp": "owasso1:A7670E_LASE_23P_12+11"}
parts["J7"] = {"ref": "J7", "value": "Waveshare-3.5in-18pin-FPC",
                "fp": "Connector_FFC-FPC:Hirose_FH12-18S-0.5SH_1x18-1MP_P0.50mm_Horizontal"}
remove_ref("J6")
for pin, net in [("1", "3V3"), ("2", "GND"), ("3", "I2C_SDA"),
                 ("4", "I2C_SCL"), ("5", "TRACKBALL_INT")]:
    add_node(net, "J6", pin)
remove_ref("J1")
# Audio-capable CC-MCore/A7670-LASE carrier. The published 23-pin interface
# is SC, SD, SR, SV, STA, TXD, RXD, RTS, PEN, P/R, GND, P/G, VEXT, VTTL,
# CTS, RI, DTR, TXD2, RXD2, VBAT, NET, VIN, VIN. The custom footprint uses
# that order across its 12-pin and 11-pin rows.
for pin, net in [
    ("1", "MIC-"), ("2", "MIC+"), ("3", "SPK-"), ("4", "SPK+"),
    ("5", "LTE_STA"), ("6", "LTE_TX"), ("7", "LTE_RX"), ("8", "LTE_RTS"),
    ("9", "LTE_PWRKEY"), ("10", "LTE_RESET"), ("11", "GND"), ("12", "GND"),
    ("13", "LTE_VEXT"), ("14", "3V3"), ("15", "LTE_CTS"), ("16", "LTE_RI"),
    ("17", "LTE_DTR"), ("18", "LTE_RX2"), ("19", "LTE_TX2"), ("20", "VBAT"),
    ("21", "LTE_NET"), ("22", "MODEM_5V"), ("23", "MODEM_5V")
]:
    add_node(net, "J1", pin)
remove_ref("J7")
for pin, net in [("1", "3V3"), ("2", "LCD_BL"), ("3", "GND"),
                 ("4", "SPI_SCK"), ("5", "SPI_MOSI"), ("6", "SPI_MISO"),
                 ("7", "LCD_DC"), ("8", "LCD_RESET"), ("9", "LCD_CS"),
                 ("10", "SD_CS"), ("12", "TP_RESET"),
                 ("13", "I2C_SCL"), ("14", "I2C_SDA"),
                 ("15", "TOUCH_INT")]:
    add_node(net, "J7", pin)

# Pins 11, 16, 17, and 18 on the selected Waveshare 18-pin FPC are not
# signal contacts in the published host interface.  Leave them unassigned;
# do not invent connections merely to make the connector appear complete.

# Use the documented ESP32-S3-EYE-style 24-pin camera interface.  This is a
# raw OV2640-style flex interface, not the arbitrary sequential mapping that
# was previously used.  The three camera supply nets intentionally remain
# explicit until the selected camera module (raw sensor vs regulated carrier)
# is frozen and its regulator circuitry is added.
remove_ref("J8")
for pin, net in [
    ("2", "GND"), ("3", "I2C_SDA"), ("4", "CAM_2V8"),
    ("5", "I2C_SCL"), ("6", "CAM_RESET"), ("7", "CAM_VSYNC"),
    ("8", "CAM_PWDN"), ("9", "CAM_HREF"), ("10", "CAM_1V5"),
    ("11", "CAM_2V8"), ("12", "CAM_D7"), ("13", "CAM_XCLK"),
    ("14", "CAM_D6"), ("15", "GND"), ("16", "CAM_D5"),
    ("17", "CAM_PCLK"), ("18", "CAM_D4"), ("19", "CAM_D0"),
    ("20", "CAM_D3"), ("21", "CAM_D1"), ("22", "CAM_D2")
]:
    add_node(net, "J8", pin)

# Molex 104031-0811 uses the SD physical contact numbering, not a generic
# six-pin header.  SPI mode leaves DAT1/DAT2 open, uses DAT3 as CS, CMD as
# MOSI, DAT0 as MISO, and exposes the two card-detect switch contacts.
remove_ref("J9")
for pin, net in [("2", "SD_CS"), ("3", "SPI_MOSI"), ("4", "3V3"),
                 ("5", "SPI_SCK"), ("6", "GND"), ("7", "SPI_MISO"),
                 ("9", "SD_DET"), ("10", "GND")]:
    add_node(net, "J9", pin)

# The keypad is an actual 4x4 diode-isolated matrix, not only a header.
for ref in [f"SW{i}" for i in range(2, 18)] + [f"D{i}" for i in range(2, 18)]:
    parts.pop(ref, None)
for name in list(nodes):
    if name.startswith("KEY_"):
        nodes.pop(name, None)
parts["J11"] = {"ref": "J11", "value": "Keypad-matrix-4x4",
                "fp": "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical"}
for i in range(16):
    add_part(f"SW{i+2}", f"KEY-{i+1}", "Button_Switch_SMD:SW_SPST_B3S-1000")
    add_part(f"D{i+2}", f"1N4148W-KEY-{i+1}", "Diode_SMD:D_SOD-123")

# Rail corrections: the 5 V RDM6300 and LTE carrier use the boosted rail.
remove_node("RFID_EN", "J5", "5")
remove_node("3V3", "J5", "1")
add_node("MODEM_5V", "J5", "1")

add_node("VBAT", "J13", "1")
add_node("GND", "J13", "2")
add_node("VBAT", "U8", "5")
add_node("VBAT", "U8", "4")
add_node("GND", "U8", "2")
add_node("BOOST_SW", "U8", "1")
add_node("BOOST_FB", "U8", "3")
add_node("MODEM_5V", "U8", "6")
add_node("VBAT", "L1", "1")
add_node("BOOST_SW", "L1", "2")
add_node("BOOST_SW", "D18", "1")
add_node("MODEM_5V", "D18", "2")
add_node("MODEM_5V", "C1", "1")
add_node("GND", "C1", "2")
add_node("VBAT", "C2", "1")
add_node("GND", "C2", "2")
add_node("3V3", "C3", "1")
add_node("GND", "C3", "2")
add_node("VBUS5V", "C4", "1")
add_node("GND", "C4", "2")
add_node("BOOST_FB", "R2", "2")
add_node("MODEM_5V", "R2", "1")
add_node("BOOST_FB", "R3", "1")
add_node("GND", "R3", "2")

# TPS61023 DRL pinout: 1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 VOUT.
remove_ref("U8")
for pin, net in [("1", "BOOST_FB"), ("2", "VBAT"), ("3", "VBAT"),
                 ("4", "GND"), ("5", "BOOST_SW"), ("6", "MODEM_5V")]:
    add_node(net, "U8", pin)

# Raw OV2640 camera rails based on the ESP32-S3-EYE reference design.
for ref in ("U9", "U10", "C5", "C6", "C7", "C8", "R6", "R7"):
    remove_ref(ref)
for pin, net in [("1", "3V3"), ("2", "GND"), ("3", "3V3"), ("5", "CAM_2V8")]:
    add_node(net, "U9", pin)
for pin, net in [("1", "3V3"), ("2", "GND"), ("3", "3V3"), ("5", "CAM_1V5")]:
    add_node(net, "U10", pin)
for ref, pinmap in {
    "C5": (("1", "3V3"), ("2", "GND")),
    "C6": (("1", "CAM_2V8"), ("2", "GND")),
    "C7": (("1", "3V3"), ("2", "GND")),
    "C8": (("1", "CAM_1V5"), ("2", "GND")),
    "R6": (("1", "CAM_2V8"), ("2", "CAM_RESET")),
    "R7": (("1", "CAM_PWDN"), ("2", "GND")),
}.items():
    for pin, net in pinmap:
        add_node(net, ref, pin)

# PCF8574T pinout: P0..P3 are keypad rows, P4..P7 are columns, INT is
# active-low, SDA/SCL are pins 15/14, and A0..A2 are tied low for address
# 0x20.  The old draft incorrectly put IR_RX on address pin A1 and left the
# matrix expander electrically unbound.
for net in list(nodes):
    nodes[net] = [n for n in nodes[net]
                  if not (n[0] == "U2" and n[1] in
                          {"1", "2", "3", "4", "5", "6", "7", "9", "10", "11", "12", "13", "14", "15", "16"})]
for pin, net in [("1", "KEY_R1"), ("2", "KEY_R2"), ("3", "KEY_R3"),
                 ("4", "KEY_R4"), ("5", "KEY_C1"), ("6", "KEY_C2"),
                 ("7", "KEY_C3"), ("9", "KEY_C4"), ("10", "GND"),
                 ("11", "GND"), ("12", "GND"), ("13", "EXP_INT"),
                 ("14", "I2C_SCL"), ("15", "I2C_SDA"), ("16", "3V3")]:
    add_node(net, "U2", pin)

# ESP32-S3-WROOM-1 module pads are module pad numbers, not GPIO numbers.
# Rebind all functional U1 signals to the selected exposed GPIO allocation.
# Pad mapping used here follows the Espressif WROOM-1 pinout:
# 1=GND, 2=3V3, 3=EN, 4..14=GPIO4..20 (with GPIO8/19/20 in their documented
# positions), 15=GPIO3, 16=GPIO46, 17..26=GPIO9..21/47/48/45, 27=GPIO0,
# 28..35=GPIO35..42, 36=U0RXD/GPIO44, 37=U0TXD/GPIO43, 38=GPIO2,
# 39=GPIO1, 40=GND, 41=EPAD/GND.
for net in list(nodes):
    nodes[net] = [n for n in nodes[net] if n[0] != "U1"]
for pin in ("2",):
    add_node("3V3", "U1", pin)
for pin in ("1", "40", "41"):
    add_node("GND", "U1", pin)
u1_map = {
    "I2C_SDA": "39", "I2C_SCL": "38",
    "CAM_D0": "4", "CAM_D1": "5", "CAM_D2": "6", "CAM_D3": "7",
    "CAM_D4": "12", "CAM_D5": "9", "CAM_D6": "8", "CAM_D7": "10",
    "CAM_XCLK": "20", "CAM_PCLK": "21", "CAM_VSYNC": "22", "CAM_HREF": "23",
    "CAM_PWDN": "24", "CAM_RESET": "25",
    "USB_D-": "13", "USB_D+": "14",
    "SPI_SCK": "28", "SPI_MOSI": "29", "SPI_MISO": "30",
    "LCD_CS": "31", "LCD_DC": "32", "LCD_BL": "33", "SD_CS": "34",
    "CC1101_CS": "26", "CC1101_GDO0": "27",
    "SX1262_CS": "16", "SX1262_DIO1": "17", "SX1262_BUSY": "15",
    "SX1262_RESET": "19", "IR_TX": "35",
    "LTE_TX": "37", "LTE_RX": "36", "LTE_PWRKEY": "18", "LTE_RI": "11"
}
for net, pin in u1_map.items():
    if net in nodes:
        add_node(net, "U1", pin)
remove_node("GND", "U3", "2")
add_node("U3_PROG", "U3", "2")
add_node("U3_PROG", "R1", "1")
add_node("GND", "R1", "2")

# USB-C device-role identification.  CC1/CC2 Rd pull-downs allow a charger or
# host to detect this phone as a sink/device while D+/D- remain available for
# ESP32-S3 USB serial/HID use (including BadUSB-style HID firmware).
add_node("USB_CC1", "USB1", "A5")
add_node("USB_CC1", "R4", "1")
add_node("GND", "R4", "2")
add_node("USB_CC2", "USB1", "B5")
add_node("USB_CC2", "R5", "1")
add_node("GND", "R5", "2")

# DW01A gate/control nets and the dual protection FET. Battery negative is the
# protected reference in this first discrete implementation.
for pin, net in [("1", "DW01A_OD"), ("2", "GND"), ("3", "DW01A_OC"), ("4", "GND")]:
    add_node(net, "U4", pin)
for pin, net in [("1", "DW01A_OD"), ("2", "GND"), ("3", "GND"),
                ("4", "DW01A_OC"), ("5", "GND"), ("6", "GND")]:
    add_node(net, "Q1", pin)

# Matrix mapping: each switch is row-to-diode, each diode goes to a column.
for i in range(16):
    row = i // 4 + 1
    col = i % 4 + 1
    mid = f"KEY_D{i+1}"
    sw = f"SW{i+2}"
    diode = f"D{i+2}"
    add_node(f"KEY_R{row}", sw, "1")
    add_node(mid, sw, "2")
    add_node(mid, diode, "1")
    add_node(f"KEY_C{col}", diode, "2")

# J11 is the optional external keypad harness.  Keep it electrically
# identical to the expander-side matrix: four rows followed by four columns.
for i in range(4):
    add_node(f"KEY_R{i+1}", "J11", str(i+1))
    add_node(f"KEY_C{i+1}", "J11", str(i+5))

# Camera subsystem intentionally omitted from this phone revision. Remove the
# OV2640 FPC, its dedicated 2.8 V/1.5 V regulators and camera-only passives,
# plus the ESP32 camera GPIO assignments and camera-only nets. Keeping this
# final cleanup at the end makes the generated netlist authoritative even
# though the earlier interface block documents the superseded option.
for ref in ("J8", "U9", "U10", "C5", "C6", "C7", "C8", "R6", "R7"):
    parts.pop(ref, None)
    remove_ref(ref)
camera_pins = {"4", "5", "6", "7", "8", "9", "10", "12", "20", "21", "22", "23", "24", "25"}
for net in list(nodes):
    nodes[net] = [n for n in nodes[net]
                  if not (n[0] == "U1" and n[1] in camera_pins)]
    if net.startswith("CAM_") or not nodes[net]:
        nodes.pop(net, None)

# Ebyte E22-900M22S physical 22-pad land pattern. The earlier J3 1x09
# adapter mapping is not pin-compatible with the SMD module, so bind only the
# documented SPI/control pads and leave RF/PA-control pads unassigned.
remove_ref("J3")
for pin, net in [("1", "GND"), ("2", "GND"), ("3", "GND"),
                 ("4", "GND"), ("5", "GND"), ("9", "3V3"),
                 ("10", "GND"), ("11", "GND"), ("12", "GND"),
                 ("13", "SX1262_DIO1"), ("14", "SX1262_BUSY"),
                 ("15", "SX1262_RESET"), ("16", "SPI_MISO"),
                 ("17", "SPI_MOSI"), ("18", "SPI_SCK"),
                 ("19", "SX1262_CS"), ("20", "GND"), ("22", "GND")]:
    add_node(net, "J3", pin)
parts["J3"] = {"ref": "J3", "value": "E22-900M22S-915MHz-SX1262",
                "fp": "owasso1:E22-400M22S"}

data = {"parts": sorted(parts.values(), key=lambda p: p["ref"]),
        "nets": [{"name": n, "nodes": v} for n, v in sorted(nets.items()) if v]}
(root / "netlist_draft.json").write_text(json.dumps(data, indent=2) + "\n")
print(f"Rev-D netlist: {len(data['parts'])} parts, {len(data['nets'])} nets")
