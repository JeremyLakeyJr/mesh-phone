#!/usr/bin/env python3
"""Rebuild owasso1.kicad_pcb with REAL library footprints + bound nets.
Uses pcbnew API. Run: LD_LIBRARY_PATH=~/.local/kicad-compat python3 rebuild_pcb.py
"""
import os, sys, json
os.environ["LD_LIBRARY_PATH"] = os.path.expanduser("~/.local/kicad-compat")
import pcbnew

BOARD_PATH = "/home/lakey/Documents/owasso1-pcb/owasso1.kicad_pcb"
FP_BASE = "/usr/share/kicad/footprints"
draft = json.load(open("/home/lakey/Documents/owasso1-pcb/netlist_draft.json"))

# Shift the complete generated board so its 87 x 154 mm center is at (137,109).
BOARD_OFFSET = (90.5, 29.0)  # local center (46.5,80) -> requested center

PLACEMENTS = {
    # Front/top: display and camera connectors. Keep the ESP32 antenna
    # at the opposite end of the board from the LTE and sub-GHz modules.
    "J7": (35, 10),
    # Put the camera FPC beside the ESP32 camera-side pads so D0/D1 do not
    # have to cross the entire board.
    "J8": (62, 15),
    "U1": (28, 45),

    # Storage and user-accessible cards on the right/left side walls.
    "J9": (24, 75),
    "J10": (80, 70),

    # RF modules at separated board edges with antenna exits into the case.
    # Move the LTE header down while keeping its edge access; this shortens
    # the U1-to-LTE control/UART crossings.
    "J1": (54, 85),
    "J2": (8, 78),
    "J3": (68, 25),
    "J4": (8, 130),
    "J5": (80, 115),

    # Input devices near the lower/front end of the phone.
    "J6": (28, 95),
    "U2": (80, 90),
    "J11": (66, 112),
    "J12": (66, 132),
    # Side-accessible power switch on the left wall, clear of the keypad.
    "SW1": (8, 55),

    # Power section kept together at the lower edge, away from RF inputs.
    # Lower-right power bank: keep switching/feedback parts together and
    # leave the keypad field clear of their high-current routes.
    "U3": (64, 130), "U4": (74, 130), "U5": (84, 130), "U6": (50, 120),
    "USB1": (66, 50),
    "D1": (10.5, 7.0), "U7": (25, 65),
    "J13": (84, 45), "U8": (70, 145), "L1": (80, 145),
    "C1": (86, 135), "C2": (50, 140), "C3": (86, 148), "C4": (76, 55),
    "R1": (64, 150), "R2": (70, 153), "R3": (80, 153),
    "R4": (58, 45), "R5": (58, 55), "Q1": (64, 140),
    "SW2": (20, 111), "SW3": (38, 111), "SW4": (56, 111),
    "SW5": (20, 123), "SW6": (38, 123), "SW7": (56, 123),
    "SW8": (20, 135), "SW9": (38, 135), "SW10": (56, 135),
}

# Four-by-four keypad. Each diode sits below its switch on B.Cu.
for i in range(16):
    col, row = i % 4, i // 4
    x = 14 + col * 14
    y = 111 + row * 12
    PLACEMENTS[f"SW{i+2}"] = (x, y)
    PLACEMENTS[f"D{i+2}"] = (x, y + 5.5)

ROTATIONS = {"J1": 90, "J6": 90, "J9": 90, "J10": 90, "USB1": 90, "U7": 90, "SW1": -90}

# ref -> (footprint lib dir, footprint name)
FP_MAP = {
    "U1": ("RF_Module.pretty", "ESP32-S3-WROOM-1"),
    "U2": ("Package_SO.pretty", "SOIC-16_4.55x10.3mm_P1.27mm"),
    "U3": ("Package_SO.pretty", "HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.3x2.3mm"),
    "U4": ("Package_TO_SOT_SMD.pretty", "SOT-23-6"),
    "U5": ("Package_TO_SOT_SMD.pretty", "SOT-23-5"),
    "U6": ("Connector_PinHeader_1.27mm.pretty", "PinHeader_1x04_P1.27mm_Vertical"),
    "J1": ("owasso1.pretty", "A7670E_LASE_23P_12+11"),
    "J2": ("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical"),
    "J3": ("owasso1.pretty", "E22-400M22S"),
    "J4": ("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x04_P2.54mm_Vertical"),
    "J5": ("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x05_P2.54mm_Vertical"),
    "J6": ("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x05_P2.54mm_Vertical"),
    "J7": ("Connector_FFC-FPC.pretty", "Hirose_FH12-18S-0.5SH_1x18-1MP_P0.50mm_Horizontal"),
    "J8": ("Connector_FFC-FPC.pretty", "Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal"),
    "J9": ("Connector_Card.pretty", "microSD_HC_Molex_104031-0811"),
    "J10": ("Connector_JAE.pretty", "JAE_SIM_Card_SF72S006"),
    "J11": ("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical"),
    "J12": ("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x04_P2.54mm_Vertical"),
    "SW1": ("Button_Switch_THT.pretty", "SW_Slide_SPDT_Angled_CK_OS102011MA1Q"),
    "USB1": ("Connector_USB.pretty", "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal"),
    "D1": ("LED_SMD.pretty", "LED_0805_2012Metric"),
    "U7": ("OptoDevice.pretty", "Vishay_MINIMOLD-3Pin"),
    "J13": ("Connector_JST.pretty", "JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal"),
    "U8": ("Package_TO_SOT_SMD.pretty", "SOT-563"),
    "U9": ("Package_TO_SOT_SMD.pretty", "SOT-23-5"),
    "U10": ("Package_TO_SOT_SMD.pretty", "SOT-23-5"),
    "L1": ("Inductor_SMD.pretty", "L_1210_3225Metric"),
    "C1": ("Capacitor_SMD.pretty", "C_1206_3216Metric"),
    "C2": ("Capacitor_SMD.pretty", "C_1206_3216Metric"),
    "C3": ("Capacitor_SMD.pretty", "C_1206_3216Metric"),
    "C4": ("Capacitor_SMD.pretty", "C_1206_3216Metric"),
    "C5": ("Capacitor_SMD.pretty", "C_1206_3216Metric"),
    "C6": ("Capacitor_SMD.pretty", "C_1206_3216Metric"),
    "C7": ("Capacitor_SMD.pretty", "C_1206_3216Metric"),
    "C8": ("Capacitor_SMD.pretty", "C_1206_3216Metric"),
    "R1": ("Resistor_SMD.pretty", "R_0805_2012Metric"),
    "R2": ("Resistor_SMD.pretty", "R_0805_2012Metric"),
    "R3": ("Resistor_SMD.pretty", "R_0805_2012Metric"),
    "R4": ("Resistor_SMD.pretty", "R_0805_2012Metric"),
    "R5": ("Resistor_SMD.pretty", "R_0805_2012Metric"),
    "R6": ("Resistor_SMD.pretty", "R_0805_2012Metric"),
    "R7": ("Resistor_SMD.pretty", "R_0805_2012Metric"),
    "Q1": ("Package_TO_SOT_SMD.pretty", "SOT-23-6"),
}

for _ref in [f"SW{i}" for i in range(2, 18)]:
    FP_MAP[_ref] = ("Button_Switch_SMD.pretty", "SW_Push_1P1T_NO_CK_KMR2")
for _ref in [f"D{i}" for i in range(2, 18)]:
    FP_MAP[_ref] = ("Diode_SMD.pretty", "D_SOD-123")

board = pcbnew.CreateEmptyBoard()

# Match the actual footprints used here: the ESP32 module's thermal-via
# array uses 0.20 mm drills, and the USB-C shell NPTH has 0.194 mm copper
# clearance to its adjacent ground pads. These are intentional footprint
# geometry constraints, not routing exceptions.
design = board.GetDesignSettings()
design.m_MinThroughDrill = pcbnew.FromMM(0.20)
design.m_HoleClearance = pcbnew.FromMM(0.18)

# --- Edge.Cuts outline 3..90 x 3..157 (87 x 154 mm phone PCB) ---
def mm(v): return pcbnew.VECTOR2I(int(pcbnew.FromMM(v)), 0)
edge_layer = board.GetLayerID("Edge.Cuts")
pts = [(3 + BOARD_OFFSET[0], 3 + BOARD_OFFSET[1]),
       (90 + BOARD_OFFSET[0], 3 + BOARD_OFFSET[1]),
       (90 + BOARD_OFFSET[0], 157 + BOARD_OFFSET[1]),
       (3 + BOARD_OFFSET[0], 157 + BOARD_OFFSET[1])]
for i in range(4):
    x1,y1 = pts[i]; x2,y2 = pts[(i+1)%4]
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetStart(pcbnew.VECTOR2I(*map(pcbnew.FromMM,(x1,y1))))
    seg.SetEnd(pcbnew.VECTOR2I(*map(pcbnew.FromMM,(x2,y2))))
    seg.SetLayer(edge_layer)
    seg.SetWidth(pcbnew.FromMM(0.1))
    board.Add(seg)

# --- Nets ---
nets = {}
for n in draft["nets"]:
    ni = pcbnew.NETINFO_ITEM(board, n["name"])
    board.Add(ni)
    nets[n["name"]] = ni
gnd = nets["GND"]

# --- Footprints ---
loaded = {}
errors = []
SKIP_PCB = {"J11", "J12"}  # external keypad/audio harnesses; onboard matrix remains
# Back-side assembly: keep the RF transceiver and the complete battery/boost
# chain together so the front remains available for the display, keypad, and
# user-accessible connectors.
BACK_REFS = {
    "J3", "J13", "U3", "U4", "U5", "U8", "L1", "C1", "C2", "C3",
    "Q1", "R1", "R2", "R3",
}
for p in draft["parts"]:
    ref = p["ref"]
    if ref in SKIP_PCB:
        continue
    if ref not in FP_MAP:
        errors.append(f"{ref}: no FP_MAP entry"); continue
    libdir, fpname = FP_MAP[ref]
    fp_root = "/home/lakey/Documents/owasso1-pcb" if libdir == "owasso1.pretty" else FP_BASE
    path = os.path.join(fp_root, libdir, fpname + ".kicad_mod")
    if not os.path.exists(path):
        errors.append(f"{ref}: missing {path}"); continue
    fp = pcbnew.FootprintLoad(os.path.join(fp_root, libdir), fpname)
    if fp is None:
        errors.append(f"{ref}: FootprintLoad failed for {fpname}"); continue
    fp.SetReference(ref)
    fp.SetValue(p["value"])
    x, y = PLACEMENTS.get(ref, (28, 60))
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x + BOARD_OFFSET[0]),
                                   pcbnew.FromMM(y + BOARD_OFFSET[1])))
    if ref in ROTATIONS:
        fp.SetOrientationDegrees(ROTATIONS[ref])
    # Keep the keypad expander on the back side so its SOIC courtyard does
    # not overlap the ESP32 module and its antenna keepout on the top side.
    flip_back = ref == "U2" or ref in {f"D{i}" for i in range(2, 18)} or ref in BACK_REFS
    if ref == "U8":
        # The DRL/SOT563 land pattern has 0.15 mm pad-to-pad copper gaps;
        # apply the package's verified local clearance while retaining the
        # board's 0.20 mm inter-net routing rule.
        for pad in fp.Pads():
            pad.SetLocalClearance(pcbnew.FromMM(0.15))
    board.Add(fp)
    if flip_back:
        # pcbnew requires a footprint to belong to a board before Flip(); this
        # mirrors pads, silkscreen, and fab geometry onto the back correctly.
        fp.Flip(fp.GetPosition(), True)
        # Some library footprints explicitly store SMD pads on F.Cu, and the
        # pcbnew Python flip helper does not rewrite those pad-layer masks.
        # Force only SMD pads to B.Cu; through-hole pads remain plated through.
        for pad in fp.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                pad.SetLayer(pcbnew.B_Cu)
    loaded[ref] = fp
    # bind pads to nets by pin name/number
    pad_map = {}
    for n in draft["nets"]:
        for node_ref, node_pin in n["nodes"]:
            if node_ref == ref:
                pad_map[str(node_pin)] = n["name"]
                pad_map[node_pin] = n["name"]
    # The schematic uses logical 1..N adapter pins for card sockets, while
    # the production footprints use the card-standard contact names.
    if ref == "J9":
        # Molex 104031-0811: 1=DAT2, 2=DAT3/CS, 3=CMD/MOSI,
        # 4=VDD, 5=CLK, 6=VSS, 7=DAT0/MISO, 8=DAT1.  Pads 9/10 are
        # the card-detect switch; expose it as a normally-open input.
        pad_map = {"2": "SD_CS", "3": "SPI_MOSI", "4": "3V3",
                   "5": "SPI_SCK", "6": "GND", "7": "SPI_MISO",
                   "9": "SD_DET", "10": "GND"}
    elif ref == "J10":
        pad_map = {"C1": "3V3", "C5": "GND", "C3": "SIM_CLK",
                   "C2": "SIM_RST", "C7": "SIM_IO", "CSW": "SIM_DET"}
    bound = 0
    for pad in fp.Pads():
        num = pad.GetNumber()
        if num in pad_map:
            pad.SetNet(nets[pad_map[num]])
            bound += 1
    print(f"{ref}: {len(list(fp.Pads()))} pads, {bound} net-bound")

# --- Mounting holes ---
for i,(hx,hy) in enumerate([(6,6),(87,6),(6,154),(87,154)],1):
    fp = pcbnew.FootprintLoad(os.path.join(FP_BASE,"MountingHole.pretty"),
                              "MountingHole_2.2mm_M2")
    if fp:
        fp.SetReference(f"H{i}")
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(hx + BOARD_OFFSET[0]),
                                       pcbnew.FromMM(hy + BOARD_OFFSET[1])))
        board.Add(fp)

# --- GND zones on In1.Cu and B.Cu ---
def add_zone(layer_name):
    z = pcbnew.ZONE(board)
    z.SetLayer(board.GetLayerID(layer_name))
    z.SetNet(gnd)
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    poly = z.Outline()
    poly.NewOutline()
    for x,y in [(pcbnew.FromMM(3 + BOARD_OFFSET[0]),pcbnew.FromMM(3 + BOARD_OFFSET[1])),
                (pcbnew.FromMM(90 + BOARD_OFFSET[0]),pcbnew.FromMM(3 + BOARD_OFFSET[1])),
                (pcbnew.FromMM(90 + BOARD_OFFSET[0]),pcbnew.FromMM(157 + BOARD_OFFSET[1])),
                (pcbnew.FromMM(3 + BOARD_OFFSET[0]),pcbnew.FromMM(157 + BOARD_OFFSET[1]))]:
        poly.Append(x, y)
    board.Add(z)
add_zone("In1.Cu")
add_zone("B.Cu")

board.Save(BOARD_PATH)
print("\nSaved.", BOARD_PATH)
if errors: print("ERRORS:", *errors, sep="\n  ")
