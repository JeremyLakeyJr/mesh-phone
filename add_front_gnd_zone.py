#!/usr/bin/env python3
import os, sys
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

path = sys.argv[1]
b = pcbnew.LoadBoard(path)
gnd = b.FindNet('GND')
if not gnd:
    raise SystemExit('GND net not found')
if not any(z.GetLayer() == pcbnew.F_Cu and z.GetNetname() == 'GND' for z in b.Zones()):
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.F_Cu)
    z.SetNet(gnd)
    z.SetLocalClearance(pcbnew.FromMM(0.15))
    p = z.Outline(); p.NewOutline()
    for x, y in [(93.8,32.3),(180.2,32.3),(180.2,185.7),(93.8,185.7)]:
        p.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    b.Add(z)
for fp in b.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() == 'GND':
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
for z in b.Zones():
    if z.GetNetname() == 'GND':
        z.SetLocalClearance(pcbnew.FromMM(0.15))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
if not b.Save(path): raise SystemExit('save failed')
print(path)
