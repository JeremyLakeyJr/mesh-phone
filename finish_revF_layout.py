"""Finish RF connector access and ground stitching in the isolated revision."""
import math
from pathlib import Path
import shutil
import sys
import pcbnew

pcbnew.SwigPyIterator.next = pcbnew.SwigPyIterator.__next__
directory=Path(__file__).resolve().parent/'revF-gps-expansion'
path=directory/'owasso1.kicad_pcb'
b=pcbnew.LoadBoard(str(path))
fps={f.GetReference():f for f in b.GetFootprints()}
def vec(x,y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y))

if '--stitch' not in sys.argv:
    backup=directory/'owasso1-before-rf-ground-finish.kicad_pcb'
    if not backup.exists():
        shutil.copy2(path,backup)
    obsolete=[t for t in b.GetTracks() if t.GetNetname()=='/GPS and rear expansion/GPS_ANT']
    f=fps['J15']
    f.SetPosition(vec(96.5,127.3))
    f.SetOrientationDegrees(180)
    p1=next(p for p in f.Pads() if p.GetNumber()=='1')
    p2=next(p for p in fps['U9'].Pads() if p.GetNumber()=='11')
    trace=pcbnew.PCB_TRACK(b)
    trace.SetStart(p1.GetPosition())
    trace.SetEnd(p2.GetPosition())
    trace.SetWidth(pcbnew.FromMM(0.8))
    trace.SetLayer(pcbnew.B_Cu)
    trace.SetNet(p1.GetNet())
    b.Add(trace)
    for ref in ['C7','C12','U10']:
        for p in fps[ref].Pads():
            if p.GetNetname()=='/GND':
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    for f in b.GetFootprints():
        if f.GetReference() in ['H1','H2','H3','H4']:
            f.SetAttributes(f.GetAttributes()|pcbnew.FP_BOARD_ONLY)
    print('RF connector points toward GPS; short 0.8mm RF link replaces keepout-crossing autoroute. Stackup impedance still unverified.')
    for t in obsolete:
        b.Remove(t)
else:
    zones={z.GetLayer():z for z in b.Zones() if z.GetNetname()=='/GND' and not z.GetIsRuleArea()}
    existing=[t.GetPosition() for t in b.GetTracks() if isinstance(t,pcbnew.PCB_VIA)]
    candidates=[]
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname()=='/GND':
                x,y=p.GetPosition().x/1e6,p.GetPosition().y/1e6
                for dx,dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(-1,1),(1,-1),(-1,-1)]:
                    candidates.append((x+dx,y+dy))
    candidates += [(float(x),float(y)) for x in range(96,179,5) for y in range(35,184,5)]
    added=0
    for x,y in candidates:
        if any((p.x/1e6-x)**2+(p.y/1e6-y)**2<3.0**2 for p in existing):
            continue
        probes=[vec(x,y)]+[vec(x+0.5*math.cos(a*math.pi/8),y+0.5*math.sin(a*math.pi/8)) for a in range(16)]
        if not all(z.HitTestFilledArea(layer,p) for layer,z in zones.items() for p in probes):
            continue
        via=pcbnew.PCB_VIA(b)
        via.SetPosition(vec(x,y))
        via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
        via.SetWidth(pcbnew.FromMM(0.6))
        via.SetDrill(pcbnew.FromMM(0.3))
        via.SetNet(b.FindNet('/GND'))
        b.Add(via)
        existing.append(via.GetPosition())
        added+=1
    print(f'Added {added} GND vias only in copper-filled disks on both layers; DRC must verify them.')
b.Save(str(path))
