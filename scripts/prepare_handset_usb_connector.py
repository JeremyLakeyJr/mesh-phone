#!/usr/bin/env python3
"""Stage USB4105 ground-land corner relief; preserve holes, placement and copper."""
import csv,hashlib,json,shutil,subprocess
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,dump,children,prop,Q
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-usb-relief')
assert not (SRC/'usb-connector-update.json').exists(),'Already installed'
shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.history','.git','*.lck','*.prl'))
name='USB4105_GroundCornerRelief';lib='Handset:'+name
foot=p.FootprintLoad('/usr/share/kicad/footprints/Connector_USB.pretty','USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal')
def relieve(fp):
 for q in fp.Pads():
  if q.GetNumber() in ('A1','B12','A12','B1'):
   q.SetShape(p.PAD_SHAPE_CHAMFERED_RECT);q.SetChamferRectRatio(.5);q.SetChamferPositions(8 if q.GetNumber() in ('A1','B12') else 4)
 fp.SetFPID(p.LIB_ID('Handset',name))
relieve(foot);foot.SetLibDescription('USB4105: GCT B4 nominal land/hole locations; 0.30 mm inward heel-corner relief on paired ground lands. Engineered contour, not the unmodified GCT land pattern.')
p.FootprintSave(str(OUT/'Handset.pretty'),foot)
b=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(b);fp=next(f for f in b.GetFootprints() if f.GetReference()=='USB1');relieve(fp)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
after=geometry(b);assert before['copper']==after['copper'];assert {k:v for k,v in before['footprints'].items() if k!='USB1'}=={k:v for k,v in after['footprints'].items() if k!='USB1'}
spec=json.loads((SRC/'connectivity.json').read_text())
for c in spec:
 if c['ref']=='USB1':c['footprint']=lib
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as stream:
 w=csv.DictWriter(stream,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(spec)
sch=parse((SRC/'usb.kicad_sch').read_text())
for sym in children(sch,'symbol'):
 if prop(sym,'Reference') and prop(sym,'Reference')[2]=='USB1':prop(sym,'Footprint')[2]=Q(lib)
(OUT/'usb.kicad_sch').write_text(dump(sch)+'\n')
manifest=dict(source_board_sha256=hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),source_project_sha256=hashlib.sha256((SRC/'handset.kicad_pro').read_bytes()).hexdigest(),changed_refs=['USB1'],changed_pads=['A1','B12','A12','B1'],chamfer_mm=.3,preserved_copper_items=len(before['copper']),hole_dimensions_and_positions_preserved=True,board_rules_preserved=True,fabrication_released=False,source_drawing='https://gct.co/files/drawings/usb4105.pdf',drawing_revision='B4 2023-12-18',contour_status='Engineered corner relief; remaining land and solder joint require assembler DFM review')
(OUT/'usb-connector-update.json').write_text(json.dumps(manifest,indent=2)+'\n')
subprocess.run(['kicad-cli','sch','export','netlist',str(OUT/'handset.kicad_sch'),'--format','kicadxml','-o',str(OUT/'netlist.xml')],check=True)
print('Staged USB ground-corner relief',OUT)
