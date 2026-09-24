#!/usr/bin/env python3
"""Apply the clearance corrections identified by native KiCad DRC."""
import csv
import json
from pathlib import Path
import pcbnew as p

OUT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
marker=OUT/'population-clearance-update.json'
if marker.exists():raise SystemExit('Already applied; do not reset saved placements.')
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
moves={'C32':(115.5,79),'C33':(115.5,82),'J7':(121,91),'C38':(116.5,73),
 'C41':(83,101),'U16':(91,78),'R48':(96,31.5),'J5':(88,43),'J8':(101,44),
 'C44':(108,42),'C47':(118,65),'C48':(118,68),'C49':(118,72),'R58':(83,61)}
before={}
for f in b.GetFootprints():
    ref=f.GetReference()
    if ref in moves:
        pos=f.GetPosition();before[ref]=[p.ToMM(pos.x),p.ToMM(pos.y)]
        x,y=moves[ref];f.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)))
    # Dense passive designators belong on the assembly drawing, not over pads.
    if ref.startswith(('R','C','L')):
        f.Reference().SetLayer(p.B_Fab if f.GetLayer()==p.B_Cu else p.F_Fab)
    f.Reference().SetTextSize(p.VECTOR2I(p.FromMM(.8),p.FromMM(.8)))
    f.Reference().SetTextThickness(p.FromMM(.12))
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
spec=json.loads((OUT/'connectivity.json').read_text())
for c in spec:
    if c['ref'] in moves:c.update(zip(('x','y'),moves[c['ref']]))
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
marker.write_text(json.dumps({'before':before,'after':moves},indent=2)+'\n')
