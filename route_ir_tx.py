#!/usr/bin/env python3
import pcbnew

path = "/home/lakey/Documents/owasso1-pcb/owasso1-routed-user-edit.kicad_pcb"
b = pcbnew.LoadBoard(path)
d1 = next(f for f in b.GetFootprints() if f.GetReference() == "D1")
u1 = next(f for f in b.GetFootprints() if f.GetReference() == "U1")
dp = next(p for p in d1.Pads() if p.GetNumber() == "1")
up = next(p for p in u1.Pads() if p.GetNumber() == "35")
net = dp.GetNet()
def v(x,y): return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
def track(a,z,layer):
    t=pcbnew.PCB_TRACK(b); t.SetStart(v(*a)); t.SetEnd(v(*z)); t.SetWidth(pcbnew.FromMM(0.20)); t.SetLayer(b.GetLayerID(layer)); t.SetNet(net); b.Add(t)
def via(x,y):
    q=pcbnew.PCB_VIA(b); q.SetPosition(v(x,y)); q.SetWidth(pcbnew.FromMM(0.60)); q.SetDrill(pcbnew.FromMM(0.30)); q.SetNet(net); b.Add(q)
# Approach the ESP32 pad from the right, keeping the new path at the top
# perimeter and using B.Cu for the long run.
via(101.625,35.0); track((100.625,35.0),(101.625,35.0),"F.Cu")
track((101.625,35.0),(101.625,33.5),"B.Cu")
track((101.625,33.5),(132.0,33.5),"B.Cu")
track((132.0,33.5),(132.0,68.43),"B.Cu")
via(132.0,68.43); track((132.0,68.43),(128.35,68.43),"F.Cu")
b.Save(path)
print(path)
