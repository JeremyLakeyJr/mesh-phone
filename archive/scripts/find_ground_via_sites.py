"""Search local ground islands with conservative pad/track clearance geometry."""
from pathlib import Path
import math
import pcbnew
from cad_sexpr import parse,children,child
pcbnew.SwigPyIterator.next=pcbnew.SwigPyIterator.__next__
d=Path(__file__).resolve().parent/'revF-gps-expansion'
b=pcbnew.LoadBoard(str(d/'owasso1.kicad_pcb'))
zones=[z for z in b.Zones() if not z.GetIsRuleArea()]
pads=[p for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()!='/GND']
tracks=[t for t in b.GetTracks() if t.GetNetname()!='/GND']
def xy(p):return p.x/1e6,p.y/1e6
def clear(x,y):
    for p in pads:
        px,py=xy(p.GetPosition()); sx,sy=xy(p.GetSize())
        theta=math.radians(p.GetOrientationDegrees())
        a=(x-px)*math.cos(theta)+(y-py)*math.sin(theta)
        c=-(x-px)*math.sin(theta)+(y-py)*math.cos(theta)
        if math.hypot(max(abs(a)-sx/2,0),max(abs(c)-sy/2,0))<.405:return False
    for t in tracks:
        ax,ay=xy(t.GetStart()); cx,cy=xy(t.GetEnd())
        den=(cx-ax)**2+(cy-ay)**2
        u=max(0,min(1,((x-ax)*(cx-ax)+(y-ay)*(cy-ay))/den)) if den else 0
        width=t.GetWidth(pcbnew.F_Cu) if isinstance(t,pcbnew.PCB_VIA) else t.GetWidth()
        if math.hypot(x-ax-u*(cx-ax),y-ay-u*(cy-ay))<.405+width/2e6:return False
    return True
tree=parse((d/'owasso1.kicad_pcb').read_text())
target=[]
back=[]
for z in children(tree,'zone'):
    for poly in children(z,'filled_polygon'):
        pts=[(float(p[1]),float(p[2])) for p in children(child(poly,'pts'),'xy')]
        if child(z,'layer')[1]=='F.Cu' and 99<min(x for x,y in pts)<100 and max(y for x,y in pts)>100:target=pts
        if child(z,'layer')[1]=='B.Cu' and min(x for x,y in pts)<95:back=pts
def inside(x,y,polygon):
    hit=False
    for (a,c),(e,f) in zip(polygon,polygon[1:]+polygon[:1]):
        if (c>y)!=(f>y) and x<(e-a)*(y-c)/(f-c)+a:hit=not hit
    return hit
for region in [(100,78,105,104)]:
    candidates=[]
    for ix in range(round(region[0]*20),round(region[2]*20)):
        for iy in range(round(region[1]*20),round(region[3]*20)):
            x,y=ix/20,iy/20
            p=pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y))
            if inside(x,y,target) and inside(x,y,back) and clear(x,y): candidates.append((x,y))
    print(region,candidates[:100], 'total',len(candidates))
