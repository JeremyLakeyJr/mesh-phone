#!/usr/bin/env python3
import os, sys
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

path = sys.argv[1]
b = pcbnew.LoadBoard(path)
gnd = b.FindNet('GND')
for z in b.Zones():
    if z.GetNetname() == 'GND':
        z.SetLocalClearance(pcbnew.FromMM(0.15))

for fp in b.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() == 'GND':
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
if not b.Save(path): raise SystemExit('save failed')
print(path)
