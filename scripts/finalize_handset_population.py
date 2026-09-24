#!/usr/bin/env python3
"""Freeze inductor packages and synchronize population artifacts once."""
import copy
import csv
import json
from pathlib import Path
import pcbnew as p
from cad_sexpr import Q,parse,dump,child,children,prop

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hardware/handset-rev-a/generated'
marker=OUT/'population-finalization.json'
if marker.exists():raise SystemExit('Already finalized; preserve subsequent saved edits.')
# Remove the inherited bottom-contact courtyard, leaving the new top-contact envelope.
fpfile=OUT/'Handset.pretty/FH12A-50S-0.5SH_TopContact.kicad_mod'
for path in (fpfile,OUT/'handset.kicad_pcb'):
    data=parse(path.read_text())
    fp=data if path==fpfile else next(f for f in children(data,'footprint') if prop(f,'Reference')[2]=='J26')
    for layer in ('F.CrtYd','F.Fab'):
        geometry=[g for g in fp if isinstance(g,list) and g[0].startswith('fp_') and child(g,'layer') and child(g,'layer')[1]==layer and g[0]!='fp_text']
        # The replacement rectangles are appended last.
        for g in geometry[:-1]:fp.remove(g)
    path.write_text(dump(data)+'\n')

p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
spec=json.loads((OUT/'connectivity.json').read_text())
inductors={'L1':('XFL4020-471MEC / 0.47uH',127,126),
 'L2':('XFL4020-102MEC / 1uH',78,119),'L3':('XFL4020-222MEC / 2.2uH',127,96)}
for old in list(b.GetFootprints()):
    ref=old.GetReference()
    if ref not in inductors:continue
    value,x,y=inductors[ref];f=p.FootprintLoad(str(OUT/'Handset.pretty'),'Coilcraft_XFL4020')
    f.SetReference(ref);f.SetValue(value);f.SetFPID(p.LIB_ID('Handset','Coilcraft_XFL4020'));b.Add(f)
    f.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)));f.Flip(f.GetPosition(),False)
    f.SetPath(old.GetPath());f.Reference().SetLayer(p.B_Fab);f.Value().SetVisible(False)
    nets={pad.GetNumber():pad.GetNetname() for pad in old.Pads()}
    for pad in f.Pads():pad.SetNet(b.FindNet(nets[pad.GetNumber()]))
    b.Remove(old);old.thisown=False
    for c in spec:
        if c['ref']==ref:c.update(value=value,footprint='Handset:Coilcraft_XFL4020',x=x,y=y,angle=0)
    path=OUT/'power.kicad_sch';sch=parse(path.read_text())
    s=next(s for s in children(sch,'symbol') if prop(s,'Reference')[2]==ref)
    prop(s,'Value')[2]=Q(value);prop(s,'Footprint')[2]=Q('Handset:Coilcraft_XFL4020')
    path.write_text(dump(sch)+'\n')
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)

# Correct actual supply-output pin types, rather than adding blanket power flags.
libpath=OUT/'Handset.kicad_sym';lib=parse(libpath.read_text())
for filename,libid,numbers in [('power','Handset:BQ25185',('1',)),('nfc','Handset:ST25R3916B_AQET',('3','7','9','11'))]:
    path=OUT/(filename+'.kicad_sch');sch=parse(path.read_text())
    for data,identifier in [(child(sch,'lib_symbols'),libid),(lib,libid.split(':')[1])]:
        s=next(s for s in children(data,'symbol') if s[1]==identifier)
        for u in children(s,'symbol'):
            for pin in children(u,'pin'):
                if child(pin,'number')[1] in numbers:pin[1]='power_out'
    path.write_text(dump(sch)+'\n')

# Store the flattened ESD symbol locally so KiCad compares against its exact source.
path=OUT/'protection.kicad_sch';sch=parse(path.read_text())
oldid='Power_Protection:TPD4E05U06DQA';newid='Handset:TPD4E05U06DQA'
s=next(s for s in children(child(sch,'lib_symbols'),'symbol') if s[1]==oldid);s[1]=Q(newid)
entry=copy.deepcopy(s);entry[1]=Q('TPD4E05U06DQA');lib.append(entry)
for inst in children(sch,'symbol'):
    if child(inst,'lib_id')[1]==oldid:child(inst,'lib_id')[1]=Q(newid)
for c in spec:
    if c['libid']==oldid:c['libid']=newid
path.write_text(dump(sch)+'\n');libpath.write_text(dump(lib)+'\n')
# Q1 uses the verified G/S/D generic symbol; exact AO3400A remains its value/BOM.
path=OUT/'storage-ir.kicad_sch';sch=parse(path.read_text())
symbols=child(sch,'lib_symbols');old=next(s for s in children(symbols,'symbol') if s[1]=='Transistor_FET:AO3400A');symbols.remove(old)
source=parse(Path('/usr/share/kicad/symbols/Transistor_FET.kicad_sym').read_text())
s=copy.deepcopy(next(s for s in children(source,'symbol') if s[1]=='Q_NMOS_GSD'));s[1]=Q('Transistor_FET:Q_NMOS_GSD');symbols.append(s)
q=next(s for s in children(sch,'symbol') if prop(s,'Reference')[2]=='Q1');child(q,'lib_id')[1]=Q('Transistor_FET:Q_NMOS_GSD')
for c in spec:
    if c['ref']=='Q1':c['libid']='Transistor_FET:Q_NMOS_GSD'
path.write_text(dump(sch)+'\n')

(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
marker.write_text(json.dumps({'inductors':inductors,'note':'Physical population complete; electrical release remains blocked.'},indent=2)+'\n')
print('Inductor MPNs/footprints frozen; display courtyard and symbol contracts corrected.')
