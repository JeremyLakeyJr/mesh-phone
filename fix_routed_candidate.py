#!/usr/bin/env python3
"""Finish the imported autoroute without changing component placement."""
import pcbnew

src = "/home/lakey/Documents/owasso1-pcb/owasso1-routed-user-edit.kicad_pcb"
board = pcbnew.LoadBoard(src)
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() == "GND" and pad.GetLayerSet().Contains(pcbnew.B_Cu):
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
try:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
except Exception as exc:
    print("Zone refill skipped:", exc)
board.Save(src)
print("Saved:", src)
