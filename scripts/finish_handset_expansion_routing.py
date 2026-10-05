#!/usr/bin/env python3
"""Prune only newly added, DRC-reported dangling escape copper in the staging copy."""
import hashlib,json,shutil,subprocess
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,dump,child
from sync_handset_schematic_rebuild import geometry
from check_handset_expansion import check_board
ROOT=Path(__file__).resolve().parents[1]
SRC=Path('/tmp/handset-expansion');OUT=Path('/tmp/handset-expansion-routing')
p.SwigPyIterator.next=p.SwigPyIterator.__next__
m=json.loads((OUT/'expansion-routing.json').read_text())
assert hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest()==m['source_hashes']['handset.kicad_pcb'],'Source changed'
original=geometry(p.LoadBoard(str(SRC/'handset.kicad_pcb')))
removed=[]
for iteration in range(30):
 subprocess.run(['kicad-cli','pcb','drc',str(OUT/'handset.kicad_pcb'),'--schematic-parity','--format','json','-o',str(OUT/'drc.json')],check=True)
 drc=json.loads((OUT/'drc.json').read_text())
 dangling=[v for v in drc['violations'] if v['type'] in ('via_dangling','track_dangling')]
 if not dangling:break
 ids={item['uuid'] for v in dangling for item in v['items']}
 assert not (ids & original['copper'].keys()),'Refusing to prune original copper'
 tree=parse((OUT/'handset.kicad_pcb').read_text());found=[]
 for node in list(tree):
  if isinstance(node,list) and node[0] in ('segment','via') and str(child(node,'uuid')[1]) in ids:
   assert child(node,'net')[1]!='GND','Ground return requires review, not pruning'
   found.append(str(child(node,'uuid')[1]));tree.remove(node)
 assert set(found)==ids
 removed+=found;(OUT/'handset.kicad_pcb').write_text(dump(tree)+'\n')
 b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
 shutil.copy2(SRC/'handset.kicad_pro',OUT/'handset.kicad_pro')
else:raise RuntimeError('Dangling cleanup did not converge')
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));final=geometry(b)
assert original['footprints']==final['footprints']
for ident,entry in original['copper'].items():assert final['copper'][ident]==entry,ident
report=check_board(b);assert report['passed'],'Cleanup broke required copper'
assert not drc.get('schematic_parity',[])
assert len(drc['violations'])==4 and all(v['type']=='hole_clearance' and all('USB1' in i['description'] for i in v['items']) for v in drc['violations']),'New DRC violations remain'
m.update(removed_unused_escape_copper_ids=removed,source_copper_items=len(original['copper']),preserved_copper_items=len(original['copper']),added_copper_items=len(final['copper'].keys()-original['copper'].keys()),net_copper_change=len(final['copper'])-len(original['copper']),routes_are_construction_history=True,final_continuity_report='expansion-routing-check.json',unconnected_items=len(drc['unconnected_items']),existing_footprints_preserved=True)
from collections import defaultdict
inner=defaultdict(float)
for t in b.GetTracks():
 if t.GetClass()!='PCB_VIA' and t.GetLayer()==p.In1_Cu and t.m_Uuid.AsString() not in original['copper']:
  inner[t.GetNetname()]+=p.ToMM(t.GetLength())
m['new_in1_trace_lengths_mm']={net:round(length,3) for net,length in sorted(inner.items())}
m['filled_and_capped_via_in_pad_review_required']=['J16.8','U14.1','U14.6','U16.1']
m['electrical_and_return_path_qualification']='Pending; continuity is not current capacity, ESD clamping, signal integrity or high-frequency return validation'
(OUT/'expansion-routing.json').write_text(json.dumps(m,indent=2)+'\n')
(OUT/'expansion-routing-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Pruned',len(removed),'unused escape items; all expansion groups connected; only four inherited USB1 findings remain')
