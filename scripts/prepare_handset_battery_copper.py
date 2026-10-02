#!/usr/bin/env python3
"""Stage wider J1-to-F2 copper without moving components or unrelated routing."""
import sys,shutil,json,hashlib
from pathlib import Path
from cad_sexpr import parse,dump,child,children
from sync_handset_schematic_rebuild import geometry
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
src=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
assert not (src/'battery-copper-update.json').exists(), 'Already installed; preserve later work'
source_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in src.iterdir() if f.is_file()}
out=Path('/tmp/handset-battery-copper');out.mkdir(exist_ok=True)
for f in src.iterdir():
 if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,out/f.name)
shutil.copytree(src/'Handset.pretty',out/'Handset.pretty',dirs_exist_ok=True)
before=geometry(p.LoadBoard(str(src/'handset.kicad_pcb')))
tree=parse((src/'handset.kicad_pcb').read_text());removed=[]
for item in children(tree,'segment'):
 if child(item,'net')[1]=='BAT_PACK_POS':removed.append(str(child(item,'uuid')[1]));tree.remove(item)
(out/'handset.kicad_pcb').write_text(dump(tree)+'\n')
b=p.LoadBoard(str(out/'handset.kicad_pcb'))
P=lambda a:p.VECTOR2I(*(p.FromMM(v) for v in a))
routes=[((128.4,102.64),(128.4,104),.6),((128.4,104),(127.9,104.5),.6),((127.9,104.5),(124.2,104.5),1.2),((124.2,104.5),(124.2,101.2),1.2),((124.2,101.2),(118.2125,101.2),.6),((118.2125,101.2),(118.2125,102.2),.6),((118.2125,102.2),(118.2125,106.5),1.2),((118.2125,106.5),(118.2125,107.5),.6)]
for a,z,w in routes:
 t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(w));t.SetLayer(p.B_Cu);t.SetNet(b.FindNet('BAT_PACK_POS'));b.Add(t)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(out/'handset.kicad_pcb'),b)
shutil.copy2(src/'handset.kicad_pro',out/'handset.kicad_pro')
after=geometry(p.LoadBoard(str(out/'handset.kicad_pcb')))
assert before['footprints']==after['footprints']
assert all(after['copper'].get(k)==v for k,v in before['copper'].items() if k not in removed)
(out/'battery-copper-update.json').write_text(json.dumps(dict(source_hashes=source_hashes,removed_copper_uuids=removed,preserved_copper_items=len(before['copper'])-len(removed),added_segments=len(routes),fabrication_released=False),indent=2)+'\n')
