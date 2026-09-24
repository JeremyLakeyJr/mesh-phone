#!/usr/bin/env python3
"""Name the edge-switch variant with assembly-only body markings explicitly."""
import csv
import json
from pathlib import Path
from cad_sexpr import Q,parse,dump,child,children,prop

OUT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
name='SW_SPDT_PCM12_EdgeAssembly'
data=parse(Path('/usr/share/kicad/footprints/Button_Switch_SMD.pretty/SW_SPDT_PCM12.kicad_mod').read_text())
data[1]=Q(name)
for g in data:
    if isinstance(g,list) and g[0].startswith('fp_') and child(g,'layer') and child(g,'layer')[1]=='F.SilkS':child(g,'layer')[1]=Q('F.Fab')
(OUT/'Handset.pretty'/(name+'.kicad_mod')).write_text(dump(data)+'\n')
path=OUT/'handset.kicad_pcb';board=parse(path.read_text())
f=next(f for f in children(board,'footprint') if prop(f,'Reference')[2]=='SW19');f[1]=Q('Handset:'+name)
path.write_text(dump(board)+'\n')
path=OUT/'power.kicad_sch';sch=parse(path.read_text())
s=next(s for s in children(sch,'symbol') if prop(s,'Reference')[2]=='SW19');prop(s,'Footprint')[2]=Q('Handset:'+name)
path.write_text(dump(sch)+'\n')
spec=json.loads((OUT/'connectivity.json').read_text())
for c in spec:
    if c['ref']=='SW19':c['footprint']='Handset:'+name
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
