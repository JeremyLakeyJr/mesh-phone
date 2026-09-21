#!/usr/bin/env python3
import os, sys
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

path = sys.argv[1]
board = pcbnew.LoadBoard(path)
board.GetDesignSettings().m_TrackMinWidth = pcbnew.FromMM(0.15)
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() == 'GND' and pad.GetLayerSet().Contains(pcbnew.B_Cu):
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
try:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
except Exception as exc:
    print('Zone refill skipped:', exc)
if not board.Save(path):
    raise SystemExit('save failed')
print(path)
