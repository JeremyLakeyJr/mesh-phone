#!/usr/bin/env python3
"""Stage the J1 Pico-Lock replacement; preserve all unrelated placement/copper."""
import sys,json,shutil,csv,hashlib
from pathlib import Path
from cad_sexpr import parse,dump,child,children,prop,Q
from sync_handset_schematic_rebuild import geometry
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
src=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
assert not (src/'battery-connector-update.json').exists(), 'Already installed; preserve subsequent edits'
source_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in src.iterdir() if f.is_file()}
out=Path('/tmp/handset-battery-connector');out.mkdir(exist_ok=True)
for f in src.iterdir():
 if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,out/f.name)
shutil.copytree(src/'Handset.pretty',out/'Handset.pretty',dirs_exist_ok=True)
name='Molex_Pico-Lock_205338-0002_1x02-1MP_P2.00mm_Horizontal';lib='Connector_Molex:'+name
b=p.LoadBoard(str(src/'handset.kicad_pcb'));before=geometry(b)
old=next(f for f in b.GetFootprints() if f.GetReference()=='J1')
f=p.FootprintLoad('/usr/share/kicad/footprints/Connector_Molex.pretty',name)
b.Add(f)
f.SetReference('J1');f.SetValue('2053380002');f.SetFPID(p.LIB_ID('Connector_Molex',name))
f.SetPath(old.GetPath());f.SetSheetname(old.GetSheetname());f.SetSheetfile(old.GetSheetfile())
f.Flip(p.VECTOR2I(0,0),p.FLIP_DIRECTION_TOP_BOTTOM)
f.SetPosition(p.VECTOR2I(p.FromMM(127.4),p.FromMM(106.0)))
f.SetOrientationDegrees(180)
for pad in f.Pads():
 if pad.GetNumber() in ('1','2'):pad.SetNet(b.FindNet({'1':'BAT_PACK_POS','2':'GND'}[pad.GetNumber()]))
# Serialize the replacement separately, then remove the old duplicate by its order.
p.SaveBoard(str(out/'replacement.kicad_pcb'),b)
tree=parse((out/'replacement.kicad_pcb').read_text());matches=[x for x in children(tree,'footprint') if prop(x,'Reference')[2]=='J1']
assert len(matches)==2
for x in matches:
 if str(x[1])!=lib:tree.remove(x)
 else:child(x,'uuid')[1]=Q(old.m_Uuid.AsString())
removed={'25f656dd-087c-4c88-8759-7c9002e2647f','1f732d76-00e1-4b81-b4a7-4201a47fa045'}
for item in list(children(tree,'segment')):
 if str(child(item,'uuid')[1]) in removed:tree.remove(item)
(out/'handset.kicad_pcb').write_text(dump(tree)+'\n')
b=p.LoadBoard(str(out/'handset.kicad_pcb'))
P=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
for net,points in [('BAT_PACK_POS',[(122.7,101.2),(124.2,101.2),(124.2,104),(128.4,104),(128.4,102.64)]),('GND',[(126.4,102.64),(126.4,102.1),(127,101.5)])]:
 for a,z in zip(points,points[1:]):
  t=p.PCB_TRACK(b);t.SetStart(P(*a));t.SetEnd(P(*z));t.SetWidth(p.FromMM(.6));t.SetLayer(p.B_Cu);t.SetNet(b.FindNet(net));b.Add(t)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(out/'handset.kicad_pcb'),b)
shutil.copy2(src/'handset.kicad_pro',out/'handset.kicad_pro')
after=geometry(p.LoadBoard(str(out/'handset.kicad_pcb')))
assert all(after['copper'].get(k)==v for k,v in before['copper'].items() if k not in removed)
assert {k:v for k,v in before['footprints'].items() if k!='J1'}=={k:v for k,v in after['footprints'].items() if k!='J1'}
spec=json.loads((src/'connectivity.json').read_text())
for c in spec:
 if c['ref']=='J1':c.update(value='2053380002',footprint=lib,x=127.4,y=106.0,angle=180)
(out/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (out/'placement.csv').open('w') as stream:
 w=csv.DictWriter(stream,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
sch=parse((src/'power.kicad_sch').read_text())
for sym in children(sch,'symbol'):
 if prop(sym,'Reference') and prop(sym,'Reference')[2]=='J1':
  prop(sym,'Value')[2]=Q('2053380002');prop(sym,'Footprint')[2]=Q(lib)
(out/'power.kicad_sch').write_text(dump(sch)+'\n')
manifest=dict(source_hashes=source_hashes,preserved_copper_items=len(before['copper'])-len(removed),removed_copper_uuids=sorted(removed),added_copper_items=6,changed_refs=['J1'],fabrication_released=False)
(out/'battery-connector-update.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Staged J1 replacement; run native DRC, parity and continuity before installation')
