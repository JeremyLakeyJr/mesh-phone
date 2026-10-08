#!/usr/bin/env python3
"""Stage the SX1262 local regulator loop without altering existing copper."""
import csv, hashlib, json, shutil
from pathlib import Path
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-sx1262-regulator')
assert not (SRC/'sx1262-regulator-routing.json').exists(), 'Already installed'
shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".history",".git","*.lck","*.prl"))
b=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(b);b.BuildConnectivity()
pads={q.m_Uuid.AsString():q for f in b.GetFootprints() for q in f.Pads()}
groups=[];seen=set()
for uid,q in pads.items():
 if uid in seen:continue
 group=({v.m_Uuid.AsString() for v in b.GetConnectivity().GetConnectedItems(q)}&pads.keys())|{uid}
 groups.append(group);seen|=group
fps={f.GetReference():f for f in b.GetFootprints()}
fps['L12'].SetOrientationDegrees(fps['L12'].GetOrientationDegrees()+180)
P=lambda xy:p.VECTOR2I(*(p.FromMM(v) for v in xy))
def track(net,points,width=.25):
 for a,z in zip(points,points[1:]):
  t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(width));t.SetLayer(p.B_Cu);t.SetNet(b.FindNet(net));b.Add(t)
def via(pos):
 v=p.PCB_VIA(b);v.SetPosition(P(pos));v.SetWidth(p.FromMM(.5));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet('GND'));b.Add(v)
track('SX_DCC_SW',[(112.75,34.0625),(112.75,32.35),(111.9,31.5)])
track('SX_VREG',[(111.75,34.0625),(111.75,33.55),(110.1,31.9),(110.1,31.5)])
track('SX_VREG',[(110.1,31.5),(109.6,30.6),(108.2,30.6),(107.82,30.98),(107.82,31.5)])
track('GND',[(108.78,31.5),(108.78,32.35),(108.8,33.5)])
via((108.8,33.5))
track('GND',[(112.25,34.0625),(112.25,35.25),(113,36)],.25)
track('GND',[(111.0625,35.25),(112.25,35.25)],.2)
p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity()
for group in groups:
 uid=next(iter(group));connected={v.m_Uuid.AsString() for v in b.GetConnectivity().GetConnectedItems(pads[uid])}|{uid}
 assert group<=connected, 'Lost existing pad connection'
after=geometry(b)
assert all(after['copper'][k]==v for k,v in before['copper'].items())
assert all(after['footprints'][k]==v for k,v in before['footprints'].items() if k!='L12')
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
spec=json.loads((OUT/'connectivity.json').read_text())
for c in spec:
 if c['ref']=='L12':c['angle']=fps['L12'].GetOrientationDegrees()
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
m=dict(source_board_sha256=hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),rotated_refs=['L12'],preserved_copper_items=len(before['copper']),added_copper_items=len(after['copper'])-len(before['copper']),preserved_pad_groups=len(groups),fabrication_released=False)
(OUT/'sx1262-regulator-routing.json').write_text(json.dumps(m,indent=2)+'\n')
print(OUT)
