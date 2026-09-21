"""Replace the unsuccessful bulk-stitch experiment with island-specific vias."""
from pathlib import Path
import math
import sys
import pcbnew
from cad_sexpr import parse,children,child
pcbnew.SwigPyIterator.next=pcbnew.SwigPyIterator.__next__
d=Path(__file__).resolve().parent/'revF-gps-expansion'
path=d/'owasso1.kicad_pcb'
old=parse((d/'owasso1-before-rf-ground-finish.kicad_pcb').read_text())
old_ids={child(t,'uuid')[1] for t in children(old,'via')}
tree=parse(path.read_text())
b=pcbnew.LoadBoard(str(path))
obsolete=[t for t in b.GetTracks() if isinstance(t,pcbnew.PCB_VIA) and t.m_Uuid.AsString() not in old_ids]
if '--narrow' in sys.argv:
    obsolete=[]
zones={z.GetLayer():z for z in b.Zones() if not z.GetIsRuleArea()}
holes=[(p.GetPosition().x/1e6,p.GetPosition().y/1e6,max(p.GetDrillSize().x,p.GetDrillSize().y)/2e6) for f in b.GetFootprints() for p in f.Pads() if p.GetDrillSize().x]
holes += [(t.GetPosition().x/1e6,t.GetPosition().y/1e6,t.GetDrillValue()/2e6) for t in b.GetTracks() if isinstance(t,pcbnew.PCB_VIA) and t not in obsolete]
def inside(x,y,pts):
    hit=False
    for (ax,ay),(bx,by) in zip(pts,pts[1:]+pts[:1]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:
            hit=not hit
    return hit
def v(x,y): return pcbnew.VECTOR2I(round(x*1e6),round(y*1e6))
for z in children(tree,'zone'):
    for poly in children(z,'filled_polygon'):
        pts=[(float(p[1]),float(p[2])) for p in children(child(poly,'pts'),'xy')]
        area=abs(sum(a[0]*c[1]-c[0]*a[1] for a,c in zip(pts,pts[1:]+pts[:1])))/2
        if area>1000: continue
        if '--narrow' in sys.argv and not (area<1 or (min(x for x,y in pts)<111 and 69<min(y for x,y in pts)<79)):
            continue
        chosen=None
        for ix in range(math.ceil(min(x for x,y in pts)*5),math.floor(max(x for x,y in pts)*5)+1):
            for iy in range(math.ceil(min(y for x,y in pts)*5),math.floor(max(y for x,y in pts)*5)+1):
                x,y=ix/5,iy/5
                if not inside(x,y,pts): continue
                if any(math.hypot(x-hx,y-hy)<radius+0.15+0.25 for hx,hy,radius in holes): continue
                radius=.1 if '--narrow' in sys.argv else .26
                probes=[v(x+radius*math.cos(a*math.pi/8),y+radius*math.sin(a*math.pi/8)) for a in range(16)]
                if all(zone.HitTestFilledArea(layer,p) for layer,zone in zones.items() for p in probes):
                    chosen=x,y; break
            if chosen: break
        print(child(z,'layer')[1],round(area,3),chosen)
        if chosen:
            via=pcbnew.PCB_VIA(b)
            via.SetPosition(v(*chosen)); via.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
            via.SetWidth(pcbnew.FromMM(.5)); via.SetDrill(pcbnew.FromMM(.3)); via.SetNet(b.FindNet('/GND'))
            b.Add(via); holes.append((*chosen,.15))
for t in obsolete: b.Remove(t)
b.Save(str(path))
