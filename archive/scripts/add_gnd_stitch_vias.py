#!/usr/bin/env python3
import os, sys
os.environ['LD_LIBRARY_PATH'] = os.path.expanduser('~/.local/kicad-compat')
import pcbnew

path = sys.argv[1]
b = pcbnew.LoadBoard(path)
gnd = b.FindNet('GND')
positions = [
    (100.0, 40.0), (145.0, 40.0), (176.0, 40.0),
    (100.0, 180.0), (145.0, 180.0), (176.0, 180.0),
]
for x,y in positions:
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(pcbnew.FromMM(0.6))
    v.SetDrill(pcbnew.FromMM(0.3))
    v.SetNetCode(gnd.GetNetCode())
    b.Add(v)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
if not b.Save(path): raise SystemExit('save failed')
print(path)
