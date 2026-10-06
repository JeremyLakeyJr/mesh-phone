#!/usr/bin/env python3
"""Stage local ESD ground pours and remove expansion inner-layer ground detours."""
import hashlib,json,shutil
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,dump,child
from sync_handset_schematic_rebuild import geometry
from check_handset_expansion import check_board
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-esd-return')
BASE=ROOT/'archive/handset-before-expansion/c7150cd5a277/handset.kicad_pcb'
assert not (SRC/'expansion-ground-update.json').exists(),'Already installed'
shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.history','.git','*.lck','*.prl'))
source=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(source)
old=geometry(p.LoadBoard(str(BASE)))['copper']
removed={t.m_Uuid.AsString():p.ToMM(t.GetLength()) for t in source.GetTracks() if t.GetClass()!='PCB_VIA' and t.GetNetname()=='GND' and t.GetLayer() in (p.In1_Cu,p.In2_Cu) and t.m_Uuid.AsString() not in old}
assert len(removed)==90,'Unexpected expansion ground routing; review before changing'
f=OUT/'handset.kicad_pcb';tree=parse(f.read_text())
tree[:]=[n for n in tree if not(isinstance(n,list) and n[0]=='segment' and str(child(n,'uuid')[1]) in removed)]
f.write_text(dump(tree)+'\n');b=p.LoadBoard(str(f))
for layer in [p.In1_Cu,p.In2_Cu]:
 z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(p.FromMM(.2));z.SetThermalReliefGap(p.FromMM(.2));z.SetThermalReliefSpokeWidth(p.FromMM(.3));z.SetMinThickness(p.FromMM(.2));z.SetZoneName('Expansion ESD return');z.SetAssignedPriority(7);z.SetPadConnection(p.ZONE_CONNECTION_FULL)
 poly=z.Outline();poly.NewOutline()
 for x,y in [(75.9,64),(111,64),(111,79.4),(85.4,79.4),(85.4,82.5),(75.9,82.5)]:poly.Append(p.FromMM(x),p.FromMM(y))
 # Preserve existing zone outlines/priority and fill only the uncovered area.
 for existing in b.Zones():
  if existing.GetLayer()==layer:poly.BooleanSubtract(existing.Outline())
 b.Add(z)
bridges=[((90.615,78),(91.385,78),.3),((83.615,76),(85.15,76),.3),((90.615,78),(89.55,78),.18),((91.385,78),(92,78),.3)]
added=[]
for a,z,width in bridges:
 t=p.PCB_TRACK(b);t.SetStart(p.VECTOR2I(*[p.FromMM(v) for v in a]));t.SetEnd(p.VECTOR2I(*[p.FromMM(v) for v in z]));t.SetWidth(p.FromMM(width));t.SetLayer(p.B_Cu);t.SetNet(b.FindNet('GND'));b.Add(t);added.append(t.m_Uuid.AsString())
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(f),b)
after=geometry(b);assert before['footprints']==after['footprints']
assert all(after['copper'].get(k)==v for k,v in before['copper'].items() if k not in removed)
assert check_board(b)['passed'],'Expansion continuity changed'
report=dict(source_board_sha256=hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),removed_ground_segment_ids=list(removed),removed_ground_length_mm=round(sum(removed.values()),3),added_ground_segment_ids=added,added_ground_length_mm=round(sum(p.ToMM(t.GetLength()) for t in b.GetTracks() if t.m_Uuid.AsString() in added),3),preserved_copper_items=len(before['copper'])-len(removed),preserved_footprints=True,original_pre_expansion_copper_preserved=len(old),ground_pours=['In1.Cu','In2.Cu'],fabrication_released=False,qualification='DC continuity and native geometry only; transient impedance, remaining plane slots, ESD placement and clamping remain unqualified')
(OUT/'expansion-ground-update.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if not k.endswith('_ids')},indent=2))
