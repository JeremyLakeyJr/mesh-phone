#!/usr/bin/env python3
"""Add conservative final escape routes to a FreeRouting candidate."""
import os
import sys
os.environ["LD_LIBRARY_PATH"] = os.path.expanduser("~/.local/kicad-compat")
import pcbnew

src, dst = sys.argv[1:3]
b = pcbnew.LoadBoard(src)
U = pcbnew.FromMM

def pos(x, y):
    return pcbnew.VECTOR2I(U(x), U(y))

def add_track(net_name, a, c, layer):
    net = b.FindNet(net_name)
    if not net:
        raise RuntimeError(f"missing net {net_name}")
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pos(*a)); t.SetEnd(pos(*c)); t.SetWidth(U(0.20))
    t.SetLayer(pcbnew.F_Cu if layer == "F.Cu" else pcbnew.B_Cu)
    t.SetNetCode(net.GetNetCode())
    b.Add(t)

def add_via(net_name, xy):
    net = b.FindNet(net_name)
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pos(*xy)); v.SetWidth(U(0.60)); v.SetDrill(U(0.30))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNetCode(net.GetNetCode())
    b.Add(v)

# Camera data escapes: short front-layer pad stubs, then bottom-layer trunks.
for net, p0, p1, p2, p3 in [
    ("CAM_D0", (19.25,43.55), (18.75,42.50), (64.75,11.80), (65.25,13.15)),
    ("CAM_D1", (19.25,44.82), (18.25,44.20), (65.75,11.80), (66.25,13.15)),
]:
    add_track(net, p0, p1, "F.Cu"); add_via(net, p1)
    add_track(net, p1, p2, "B.Cu"); add_via(net, p2)
    add_track(net, p2, p3, "F.Cu")

# LTE_RI runs from the ESP32 escape to the through-hole modem header on B.Cu.
add_track("LTE_RI", (19.25,52.44), (18.25,52.44), "F.Cu")
add_via("LTE_RI", (18.25,52.44))
add_track("LTE_RI", (18.25,52.44), (48.92,5.95), "B.Cu")

# VBAT enters at the modem header, travels on B.Cu around the left edge, and
# returns to the side switch through a single via and a short front stub.
add_track("VBAT", (59.08,5.95), (10.00,57.00), "B.Cu")
add_via("VBAT", (10.00,57.00))
add_track("VBAT", (10.00,57.00), (8.00,57.00), "F.Cu")

if not b.Save(dst):
    raise SystemExit("could not save manual-route candidate")
print(dst)
