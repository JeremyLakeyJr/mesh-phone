#!/usr/bin/env python3
"""Finish observed placement/silkscreen corrections without changing DRC rules."""
import csv
import json
from pathlib import Path
import pcbnew as p
from cad_sexpr import Q,parse,dump,children,prop,child

OUT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
marker=OUT/'clearance-finish.json'
if marker.exists():raise SystemExit('Already applied.')
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
fpname='ESP32-S3-WROOM-1_0.3mm_ThermalDrills'
template=parse(Path('/usr/share/kicad/footprints/RF_Module.pretty/ESP32-S3-WROOM-1.kicad_mod').read_text())
template[1]=Q(fpname)
for pad in children(template,'pad'):
    drill=child(pad,'drill')
    if drill and float(drill[1])==.2:drill[1]='0.3'
child(template,'descr')[1]=Q('ESP32-S3-WROOM-1 standard lands; thermal drills enlarged to 0.3mm in 0.6mm copper for project fabrication rule. Via-in-pad filling/capping requires assembly review.')
(OUT/'Handset.pretty'/(fpname+'.kicad_mod')).write_text(dump(template)+'\n')
assembly_refs={'U20','USB1','U2','Q1','U10','U4','Y1','J20','U7','H1','H2'}
for f in b.GetFootprints():
    ref=f.GetReference()
    if ref=='L3':f.SetPosition(p.VECTOR2I(p.FromMM(127),p.FromMM(96.75)))
    if ref=='U1':
        f.SetFPID(p.LIB_ID('Handset',fpname))
        for pad in f.Pads():
            if pad.GetDrillSize().x==p.FromMM(.2):pad.SetDrillSize(p.VECTOR2I(p.FromMM(.3),p.FromMM(.3)))
    if ref in assembly_refs:f.Reference().SetLayer(p.B_Fab if f.GetLayer()==p.B_Cu else p.F_Fab)
    if ref=='SW19':
        for g in f.GraphicalItems():
            if g.GetLayer()==p.F_SilkS:g.SetLayer(p.F_Fab)
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
spec=json.loads((OUT/'connectivity.json').read_text())
for c in spec:
    if c['ref']=='L3':c['y']=96.75
    if c['ref']=='U1':c['footprint']='Handset:'+fpname
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
path=OUT/'core.kicad_sch';sch=parse(path.read_text())
s=next(s for s in children(sch,'symbol') if prop(s,'Reference')[2]=='U1');prop(s,'Footprint')[2]=Q('Handset:'+fpname)
path.write_text(dump(sch)+'\n')
with (OUT/'placement.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
marker.write_text(json.dumps({'L3':[127,96.75],'thermal_drill_mm':.3,'assembly_only_refs':sorted(assembly_refs)},indent=2)+'\n')
