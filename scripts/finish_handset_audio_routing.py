#!/usr/bin/env python3
"""Prune only newly added, DRC-reported dangling escape copper in the staging copy."""
import hashlib,json,shutil,subprocess
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,dump,child
from sync_handset_schematic_rebuild import geometry
from check_handset_audio import check_board
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-audio-routing')
p.SwigPyIterator.next=p.SwigPyIterator.__next__
m=json.loads((OUT/'audio-routing.json').read_text())
assert hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest()==m['source_board_sha256'],'Source changed'
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
for ref,item in original['footprints'].items():
 if ref not in m['moved_refs']:assert final['footprints'][ref]==item
for ident,entry in original['copper'].items():assert final['copper'][ident]==entry,ident
report=check_board(b);assert report['passed'],'Cleanup broke required copper'
assert not drc.get('schematic_parity',[])
assert not drc['violations'],'New DRC violations remain'
m.update(removed_unused_escape_copper_ids=removed,added_copper_items=len(final['copper'])-len(original['copper']),routes_are_construction_history=True,final_continuity_report='audio-routing-check.json',unconnected_items=len(drc['unconnected_items']),unchanged_footprints_preserved=True,final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest())
(OUT/'audio-routing.json').write_text(json.dumps(m,indent=2)+'\n')
(OUT/'audio-routing-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('Pruned',len(removed),'unused escape items; amplifier continuity passes; zero DRC/parity findings')
