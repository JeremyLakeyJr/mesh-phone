#!/usr/bin/env python3
"""Generate OWASSO-1 rev A PCB layout via kiutils (correct API)."""
from kiutils.board import Board, Footprint, Segment, GrLine, GrText
from kiutils.items.common import Position, PageSettings

draft = json_load = None
import json
pinmap = json.load(open("/home/lakey/Documents/owasso1-pcb/pinmap.json"))
draft = json.load(open("/home/lakey/Documents/owasso1-pcb/netlist_draft.json"))

board = Board()

W, H = 56.0, 122.0
board.graphicItems.extend([
    GrLine(start=Position(X=3, Y=3), end=Position(X=W-3, Y=3), layer="Edge.Cuts", width=0.1),
    GrLine(start=Position(X=W-3, Y=3), end=Position(X=W-3, Y=H-3), layer="Edge.Cuts", width=0.1),
    GrLine(start=Position(X=W-3, Y=H-3), end=Position(X=3, Y=H-3), layer="Edge.Cuts", width=0.1),
    GrLine(start=Position(X=3, Y=H-3), end=Position(X=3, Y=3), layer="Edge.Cuts", width=0.1),
])
board.graphicItems.append(GrText(text="OWASSO-1 revA", position=Position(X=W/2, Y=H-6), layer="F.SilkS"))

placements = {
    "U1": (28, 42), "J9": (45, 45), "J10": (14, 50),
    "J7": (31, 8), "J8": (49, 12), "J6": (10, 12),
    "J2": (14, 66), "J3": (43, 66),
    "J1": (31, 92), "J4": (10, 92), "J5": (49, 92),
    "U2": (24, 112), "SW1_9": (37, 110),
    "U3": (10, 120), "U4": (16, 120), "U5": (22, 120), "U6": (28, 120),
    "USB1": (28, 119), "D_IR1": (10, 92), "U7": (14, 92), "SW_PWR": (50, 78),
}

for p in draft["parts"]:
    ref = p["ref"]
    fp_name = p.get("fp") or "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical"
    x, y = placements.get(ref, (31, 60))
    fp = Footprint()
    fp.libraryLink = fp_name
    fp.position = Position(X=x, Y=y)
    fp.referenceAttr = ref if hasattr(fp, 'referenceAttr') else None
    # kiutils Footprint: set reference/value via fpTexts
    from kiutils.items.fpitems import FpText
    fp.fpTexts = [
        FpText(type="reference", text=ref, position=Position(X=0, Y=-2.5), layer="F.SilkS"),
        FpText(type="value", text=p["value"], position=Position(X=0, Y=2.5), layer="F.Fab"),
    ]
    board.footprints.append(fp)

board.to_file("/home/lakey/Documents/owasso1-pcb/owasso1.kicad_pcb")
print(f"Wrote owasso1.kicad_pcb: {len(board.footprints)} footprints, outline {W}x{H}mm")
