"""Read filled polygons to locate islands hidden by DRC's zone-origin reporting."""
from pathlib import Path
from cad_sexpr import parse, children, child

path=Path(__file__).resolve().parent/'revF-gps-expansion/owasso1.kicad_pcb'
board=parse(path.read_text())
for z in children(board,'zone'):
    for i,p in enumerate(children(z,'filled_polygon')):
        points=[(float(q[1]),float(q[2])) for q in children(child(p,'pts'),'xy')]
        area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])))/2
        print(child(z,'layer')[1],i,'area',round(area,4),'bounds',tuple(round(v,4) for v in (min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points))))
