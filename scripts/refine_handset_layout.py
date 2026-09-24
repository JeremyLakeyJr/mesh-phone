#!/usr/bin/env python3
"""Apply the case/audio/RF placement update to the saved board, preserving edits.

Take a content-addressed snapshot before modifying the board or schematic.
Does not invoke the original generator or replace unrelated user placements.
"""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import uuid
import pcbnew as p
from cad_sexpr import Q, parse, dump, child, children, prop

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/handset-rev-a/generated'
boardpath=OUT/'handset.kicad_pcb'
snapshot=ROOT/'archive/handset-before-audio-rf'/hashlib.sha256(boardpath.read_bytes()).hexdigest()[:12]
marker=OUT/'audio-rf-update.json'
if marker.exists():
    raise SystemExit('Already applied. Edit saved board directly; refusing to reset placement.')
snapshot.mkdir(parents=True,exist_ok=True)
for source in list(OUT.glob('*.kicad_*'))+list(OUT.glob('*.json'))+list(OUT.glob('*.csv')):
    shutil.copy2(source,snapshot/source.name)
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(boardpath))
fps={f.GetReference():f for f in b.GetFootprints()}
mm=p.FromMM
v=lambda x,y:p.VECTOR2I(mm(x),mm(y))
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-audio-rf/'+s))
spec=json.loads((OUT/'connectivity.json').read_text())
changes={'U1':(82,58,270),'R1':(98,59,0),'R2':(98,62,0),'C1':(98,65,0),
 'C2':(86,72,0),'C3':(89,66,0),'J8':(101,41,0),'J4':(79,92,0),
 'J3':(88,32,0),'J5':(102,32,0),'J6':(111,165,0)}
before={}
for ref,(x,y,angle) in changes.items():
    f=fps[ref]; pos=f.GetPosition()
    before[ref]=[p.ToMM(pos.x),p.ToMM(pos.y),f.GetOrientationDegrees()]
    f.SetPosition(v(x,y));f.SetOrientationDegrees(angle)
    for c in spec:
        if c['ref']==ref:c.update(x=x,y=y,angle=angle)

# Add real GNSS module and three independent RF test/antenna connections.
# RF output labels intentionally stop at the unfinished matching networks.
entries=[
 ('U12','MAX-M10S-00B-01','RF_GPS:MAX-M10S','RF_GPS:ublox_MAX',114,48,
  {1:'GND',2:'GPS_HOST_RX',3:'GPS_HOST_TX',4:'GPS_PPS',5:None,6:None,7:'+3V3',8:'+3V3',9:None,10:'GND',11:'GPS_RF',12:'GND',13:None,14:None,15:None,16:None,17:None,18:None}),
 ('C29','100nF','Device:C','Capacitor_SMD:C_0402_1005Metric',122,48,{1:'+3V3',2:'GND'}),
 ('C30','1uF','Device:C','Capacitor_SMD:C_0402_1005Metric',122,51,{1:'+3V3',2:'GND'}),
 ('J20','LORA_915_ANT','Connector:Conn_Coaxial','Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical',113,31,{1:'LORA_RF_50R',2:'GND'}),
 ('J21','CC1101_915_ANT','Connector:Conn_Coaxial','Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical',124,31,{1:'CC_RF_50R',2:'GND'}),
 ('J22','GNSS_PASSIVE_ANT','Connector:Conn_Coaxial','Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical',126,48,{1:'GPS_RF',2:'GND'}),
]
root=parse((OUT/'handset.kicad_sch').read_text())
rootid=child(root,'uuid')[1]
sheetid=uid('rf-sheet')
sch=parse(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{sheetid}") (paper "A3") (lib_symbols))')
seen=set()
for i,(ref,value,libid,fpname,x,y,nets) in enumerate(entries):
    lib,name=libid.split(':')
    libroot=parse(Path('/usr/share/kicad/symbols',lib+'.kicad_sym').read_text())
    s=copy.deepcopy(next(s for s in children(libroot,'symbol') if s[1]==name))
    s[1]=Q(libid)
    if libid not in seen:child(sch,'lib_symbols').append(s);seen.add(libid)
    sx=63.5+(i%3)*127;sy=76.2+(i//3)*101.6
    inst=parse(f'''(symbol (lib_id "{libid}") (at {sx} {sy} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}")
     (property "Reference" "{ref}" (at {sx} {sy-25.4} 0) (effects (font (size 1.27 1.27))))
     (property "Value" "{value}" (at {sx} {sy-22.86} 0) (effects (font (size 1.27 1.27))))
     (property "Footprint" "{fpname}" (at {sx} {sy} 0) (effects (font (size 1.27 1.27)) (hide yes)))
     (instances (project "handset" (path "/{rootid}/{sheetid}" (reference "{ref}") (unit 1)))))''')
    for u in children(s,'symbol'):
        for pin in children(u,'pin'):
            number=child(pin,'number')[1];at=child(pin,'at');px=sx+float(at[1]);py=sy-float(at[2]);angle=float(at[3])
            net=nets.get(int(number));inst.append(parse(f'(pin "{number}" (uuid "{uid(ref+number)}"))'))
            if net:
                ex=px-5.08*math.cos(math.radians(angle));ey=py+5.08*math.sin(math.radians(angle))
                sch.append(parse(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+number+"wire")}"))'))
                sch.append(parse(f'(global_label "{net}" (shape input) (at {ex} {ey} {angle}) (effects (font (size 1 1)) (justify left)) (uuid "{uid(ref+number+"label")}"))'))
            else:sch.append(parse(f'(no_connect (at {px} {py}) (uuid "{uid(ref+number+"nc")}"))'))
    sch.append(inst)
    lib,name=fpname.split(':');fp=p.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',name)
    fp.SetReference(ref);fp.SetValue(value);fp.SetFPID(p.LIB_ID(lib,name));b.Add(fp)
    fp.SetPosition(v(x,y));fp.Flip(v(x,y),False)
    path=p.KIID_PATH()
    for ident in [str(rootid),sheetid,uid(ref)]:path.push_back(p.KIID(ident))
    fp.SetPath(path);fp.Reference().SetTextSize(v(.8,.8));fp.Value().SetVisible(False)
    for pad in fp.Pads():
        net=nets.get(int(pad.GetNumber())) if pad.GetNumber().isdigit() else None
        if net:
            n=b.FindNet(net)
            if not n:n=p.NETINFO_ITEM(b,net);b.Add(n)
            pad.SetNet(n)
    spec.append(dict(ref=ref,value=value,libid=libid,footprint=fpname,x=x,y=y,side='B',angle=0,sheet='gnss-antennas',nets={str(k):val for k,val in nets.items()}))
root.append(parse(f'''(sheet (at 30 190) (size 90 40) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sheetid}")
 (property "Sheetname" "gnss-antennas" (at 30 189 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "gnss-antennas.kicad_sch" (at 30 231 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project "handset" (path "/{rootid}" (page "8")))))'''))
(OUT/'gnss-antennas.kicad_sch').write_text(dump(sch)+'\n')
(OUT/'handset.kicad_sch').write_text(dump(root)+'\n')
# Remove superseded GNSS reservation graphics only, preserving other drawings.
for item in list(b.GetDrawings()):
    if isinstance(item,p.PCB_TEXT) and 'GNSS UBX-M10050' in item.GetText():b.Remove(item)
    elif isinstance(item,p.PCB_SHAPE) and item.GetLayer()==p.User_1:
        pts=[item.GetStart(),item.GetEnd()]
        if all(105.4<=p.ToMM(pt.x)<=122.6 and 42.4<=p.ToMM(pt.y)<=51.6 for pt in pts):b.Remove(item)
p.SaveBoard(str(boardpath),b)
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
reservations=json.loads((OUT/'reservations.json').read_text())
reservations=[r for r in reservations if not r[0].startswith('GNSS')]
(OUT/'reservations.json').write_text(json.dumps(reservations,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet']);writer.writeheader()
    writer.writerows({k:c[k] for k in writer.fieldnames} for c in spec)
marker.write_text(json.dumps({'snapshot':str(snapshot.relative_to(ROOT)),'previous_positions':before,'placements':changes,'added':[e[0] for e in entries]},indent=2)+'\n')
print('Updated saved PCB and added GNSS/antenna sheet. Snapshot: '+str(snapshot))
