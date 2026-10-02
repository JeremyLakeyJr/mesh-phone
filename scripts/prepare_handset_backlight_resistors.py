#!/usr/bin/env python3
"""Stage specified high-power backlight resistors without changing geometry."""
import copy,csv,hashlib,json,shutil,uuid
from pathlib import Path
from cad_sexpr import parse,dump,children,child,prop,Q
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-backlight-resistors')
assert not (SRC/'backlight-resistor-update.json').exists(),'Already installed; preserve later edits'
OUT.mkdir(exist_ok=True)
hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in SRC.iterdir() if f.is_file()}
for f in SRC.iterdir():
 if f.is_file() and f.suffix not in ('.lck','.prl'):shutil.copy2(f,OUT/f.name)
shutil.copytree(SRC/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
refs={'R52','R53','R54','R55'};mpn='CRCW0603150RFKEAHP';value='150 1% 0.33W'
for name,kind in [('display.kicad_sch','symbol'),('handset.kicad_pcb','footprint')]:
 tree=parse((SRC/name).read_text());changed=[]
 for obj in children(tree,kind):
  ref=prop(obj,'Reference')
  if ref and ref[2] in refs:
   assert prop(obj,'Value')[2]=='150 1% 0.1W'
   prop(obj,'Value')[2]=Q(value)
   field=copy.deepcopy(prop(obj,'Value'));field[1]=Q('MPN');field[2]=Q(mpn)
   if kind=='footprint':child(field,'uuid')[1]=Q(str(uuid.uuid4()))
   else:child(field,'effects').append('hide')
   obj.append(field);changed.append(str(ref[2]))
 assert set(changed)==refs
 (OUT/name).write_text(dump(tree)+'\n')
spec=json.loads((SRC/'connectivity.json').read_text())
for c in spec:
 if c['ref'] in refs:c.update(value=value,mpn=mpn,manufacturer='Vishay')
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
with (OUT/'backlight-resistor-bom.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['References','Quantity','Manufacturer','MPN','Value','Footprint','Qualification'])
 w.writerow(['R52 R53 R54 R55',4,'Vishay',mpn,value,'Resistor_SMD:R_0603_1608Metric','0.33W P70 per current datasheet; assembly thermal qualification open'])
# Compare geometry after clearing only permitted value-field differences.
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
before=geometry(p.LoadBoard(str(SRC/'handset.kicad_pcb')));after=geometry(p.LoadBoard(str(OUT/'handset.kicad_pcb')))
for ref in refs:after['footprints'][ref][5]=before['footprints'][ref][5]
assert before==after,'Unexpected geometry/copper change'
(OUT/'backlight-resistor-update.json').write_text(json.dumps(dict(source_hashes=hashes,changed_refs=sorted(refs),mpn=mpn,geometry_preserved=True,source='https://www.vishay.com/docs/20043/crcwhpe3.pdf',fabrication_released=False),indent=2)+'\n')
