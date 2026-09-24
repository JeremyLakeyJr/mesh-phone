#!/usr/bin/env python3
"""Prepare a power-entry revision in /tmp, preserving the saved project.

Candidate generation only. Native checks and continuity review precede installation.
"""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET
import pcbnew as p
import handset_additive as additive
from cad_sexpr import Q, parse, dump, child, children, prop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'hardware/handset-rev-a/generated'
OUT = Path('/tmp/handset-power-entry')
p.SwigPyIterator.next = p.SwigPyIterator.__next__
assert not (SOURCE/'power-entry-update.json').exists(), 'Already installed; preserve saved edits.'
OUT.mkdir(exist_ok=True)
for f in SOURCE.iterdir():
    if f.is_file() and f.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_sym','.json','.csv'):
        shutil.copy2(f,OUT/f.name)
for name in ('fp-lib-table','sym-lib-table'):
    shutil.copy2(SOURCE/name,OUT/name)
shutil.copytree(SOURCE/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
additive.OUT = OUT
uid = lambda s: str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-power-entry/'+s))

def chip(name, pins):
    s=parse(f'''(symbol "Handset:{name}" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "{name}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (symbol "{name}_0_1" (rectangle (start -10.16 17.78) (end 10.16 -17.78)
      (stroke (width 0.254) (type default)) (fill (type background)))))''')
    u=['symbol',Q(name+'_1_1')]
    for i,(number,label,typ) in enumerate(pins):
        right=i>=math.ceil(len(pins)/2); j=i-math.ceil(len(pins)/2) if right else i
        u.append(parse(f'''(pin {typ} line (at {15.24 if right else -15.24} {12.7-j*2.54} {180 if right else 0})
          (length 5.08) (name "{label}" (effects (font (size 1 1))))
          (number "{number}" (effects (font (size 1 1)))))'''))
    s.append(u);return s

symbols={}
def define(name, labels, types):
    symbols['Handset:'+name]=chip(name,[(str(i),label,types.get(i,'passive')) for i,label in enumerate(labels,1)])
define('TPS25200DRV',['OUT','ILIM','FAULT_N','EN','GND','IN','EP'],{1:'power_out',3:'open_collector',4:'input',5:'power_in',6:'power_in',7:'power_in'})
define('TUSB320LAI',['CC1','CC2','PORT','VBUS_DET','ADDR','OUT3','OUT1','OUT2','ID','GND','EN_N','VDD'],
       {1:'bidirectional',2:'bidirectional',3:'input',4:'input',5:'input',6:'open_collector',7:'open_collector',8:'open_collector',9:'open_collector',10:'power_in',11:'input',12:'power_in'})
define('TLV70433DBV',['GND','IN','OUT','NC','NC'],{1:'power_in',2:'power_in',3:'power_out'})
define('TCA9536DGK',['P0','P1','P2','GND','P3','SCL','SDA','VCC'],
       {1:'bidirectional',2:'bidirectional',3:'bidirectional',4:'power_in',5:'bidirectional',6:'input',7:'bidirectional',8:'power_in'})
entries=[]
def add(ref,value,libid,fp,nets,x,y,side='F',angle=0):
    entries.append(dict(ref=ref,value=value,libid=libid,footprint=fp,nets=nets,x=x,y=y,side=side,angle=angle))
def resistor(ref,value,a,z,x,y,side='F'):
    add(ref,value,'Device:R','Resistor_SMD:R_0402_1005Metric',{1:a,2:z},x,y,side)
def cap(ref,value,a,x,y,side='F',size='0603'):
    dims={'0402':'1005','0603':'1608','0805':'2012'}[size]
    add(ref,value,'Device:C',f'Capacitor_SMD:C_{size}_{dims}Metric',{1:a,2:'GND'},x,y,side)

add('U21','TPS25200DRVR','Handset:TPS25200DRV','Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm',
    {1:'USB_PROTECTED',2:'USB_ILIM',3:'USB_PWR_FAULT_N',4:'USB_PWR_EN',5:'GND',6:'USB_FUSED',7:'GND'},125,63)
add('U22','TUSB320LAIRWBR','Handset:TUSB320LAI','Package_DFN_QFN:Texas_X2QFN-12_1.6x1.6mm_P0.4mm',
    {1:'USB_CC1',2:'USB_CC2',3:'GND',4:'USB_VBUS_DET',5:None,6:None,7:'USB_CC_HIGH_N',8:None,9:None,10:'GND',11:'GND',12:'USB_AON_3V3'},121,57)
add('U23','TLV70433DBVR','Handset:TLV70433DBV','Package_TO_SOT_SMD:SOT-23-5',
    {1:'GND',2:'USB_FUSED',3:'USB_AON_3V3',4:'GND',5:'GND'},116.5,55.5)
add('U24','TCA9536DGKR','Handset:TCA9536DGK','Package_SO:VSSOP-8_3x3mm_P0.65mm',
    {1:'CHG_ENABLE',2:'USB_LEGACY_EN',3:'USB_CC_QUALIFIED_N',4:'GND',5:'USB_PWR_FAULT_N',6:'I2C_SCL',7:'I2C_SDA',8:'+3V3'},104.5,55.8,'B')
for ref,nets,x,y,side in [
    ('Q5',{1:'CHG_ENABLE',2:'GND',3:'CHG_CE_N'},115.5,66,'B'),
    ('Q7',{1:'USB_CC_AUTO',2:'GND',3:'USB_CC_QUALIFIED_N'},111,56,'F')]:
    add(ref,'AO3400A','Transistor_FET:Q_NMOS_GSD','Package_TO_SOT_SMD:SOT-23',nets,x,y,side)
add('Q6','AO3401A','Transistor_FET:Q_PMOS_GSD','Package_TO_SOT_SMD:SOT-23',
    {1:'USB_CC_HIGH_N',2:'USB_AON_3V3',3:'USB_CC_AUTO'},116.5,59.8)
add('D1','SMF5.0A / Diotec','Device:D_TVS','Diode_SMD:D_SOD-123F',
    {1:'USB_FUSED',2:'GND'},130,69,angle=90)
add('D2','BAT54C,215','Diode:BAT54C','Package_TO_SOT_SMD:SOT-23',
    {1:'USB_CC_AUTO',2:'USB_LEGACY_EN',3:'USB_PWR_EN'},122,66.5)
for ref,a,z,x,y in [('F1','USB_VBUS','USB_FUSED',130,56),('F2','BAT_PACK_POS','VBAT',119,107.5)]:
    add(ref,'046701.5NRHF / 1.5A','Device:Fuse','Fuse:Fuse_0603_1608Metric',{1:a,2:z},x,y,'B')
resistor('R65','100k 1%','USB_ILIM','GND',125,69.5)
resistor('R66','10k','+3V3','USB_PWR_FAULT_N',110,55.3,'B')
resistor('R67','100k','USB_PWR_EN','GND',125,66.5)
resistor('R68','4.7k','USB_LEGACY_EN','GND',103,59,'B')
resistor('R69','10k','+3V3','USB_CC_QUALIFIED_N',112,57,'B')
resistor('R70','4.7k','USB_CC_AUTO','GND',110,60.5)
cap('C56','100nF 50V X7R','USB_FUSED',115.5,52.5)
cap('C57','2.2uF 10V X7R','USB_AON_3V3',112.9,59.3)
cap('C58','100nF 10V X7R','USB_AON_3V3',122,59.8,size='0402')
cap('C59','100nF 50V X7R','USB_FUSED',129.5,63.5)
cap('C60','100nF 10V X7R','+3V3',101.5,53.5,'B',size='0402')
additive.add_sheet('power-entry',entries,symbols,15,(425,235))
sheet=parse((OUT/'power-entry.kicad_sch').read_text());child(sheet,'paper')[1]=Q('A1')
(OUT/'power-entry.kicad_sch').write_text(dump(sheet)+'\n')

# Modify existing symbol terminals while retaining UUIDs, sheet paths and drawings.
spec=json.loads((OUT/'connectivity.json').read_text());byref={c['ref']:c for c in spec}
def update(ref,nets=None,value=None,footprint=None,xy=None,angle=0):
    c=byref[ref]; path=OUT/(c['sheet']+'.kicad_sch');sch=parse(path.read_text())
    inst=next(s for s in children(sch,'symbol') if prop(s,'Reference')[2]==ref)
    symbol=next(s for s in children(child(sch,'lib_symbols'),'symbol') if s[1]==child(inst,'lib_id')[1])
    if ref=='U3':
        symbol[1]=Q('Handset:BQ25186')
        for sub in children(symbol,'symbol'):sub[1]=Q(str(sub[1]).replace('BQ25185','BQ25186'))
        labels={1:('SYS','power_out'),2:('BAT','power_in'),3:('PG_GPO_N','open_collector'),4:('CE_N','input'),5:('GND','power_in'),6:('TS_MR','passive'),7:('SDA','bidirectional'),8:('SCL','input'),9:('INT_N','open_collector'),10:('IN','power_in'),11:('EP','power_in')}
        for sub in children(symbol,'symbol'):
            for pin in children(sub,'pin'):
                label,typ=labels[int(child(pin,'number')[1])];child(pin,'name')[1]=Q(label);pin[1]=typ
        prop(symbol,'Value')[2]=Q('BQ25186')
        child(inst,'lib_id')[1]=Q('Handset:BQ25186');c['libid']='Handset:BQ25186'
        lib=parse((OUT/'Handset.kicad_sym').read_text());entry=copy.deepcopy(symbol);entry[1]=Q('BQ25186');lib.append(entry)
        (OUT/'Handset.kicad_sym').write_text(dump(lib)+'\n')
    if nets is not None:
        sx,sy=map(float,child(inst,'at')[1:3]);assert float(child(inst,'at')[3])==0
        for sub in children(symbol,'symbol'):
            for pin in children(sub,'pin'):
                number=str(child(pin,'number')[1]);at=child(pin,'at');px=sx+float(at[1]);py=sy-float(at[2]);a=float(at[3]);net=nets.get(number)
                eq=lambda pt:abs(float(pt[1])-px)<1e-5 and abs(float(pt[2])-py)<1e-5
                wires=[w for w in children(sch,'wire') if any(eq(pt) for pt in children(child(w,'pts'),'xy'))]
                for wire in wires:
                    other=next(pt for pt in children(child(wire,'pts'),'xy') if not eq(pt))
                    for lab in list(children(sch,'global_label')):
                        la=child(lab,'at')
                        if abs(float(la[1])-float(other[1]))<1e-5 and abs(float(la[2])-float(other[2]))<1e-5:sch.remove(lab)
                    sch.remove(wire)
                for nc in list(children(sch,'no_connect')):
                    if eq(child(nc,'at')):sch.remove(nc)
                if net:
                    ex=round(px-5.08*math.cos(math.radians(a)),6);ey=round(py+5.08*math.sin(math.radians(a)),6)
                    sch.append(parse(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+number+"w")}"))'))
                    sch.append(parse(f'(global_label "{net}" (shape input) (at {ex} {ey} {a}) (effects (font (size 1 1)) (justify left)) (uuid "{uid(ref+number+"l")}"))'))
                else:sch.append(parse(f'(no_connect (at {px} {py}) (uuid "{uid(ref+number+"nc")}"))'))
        c['nets']=nets
    if value:c['value']=value;prop(inst,'Value')[2]=Q(value)
    if footprint:c['footprint']=footprint;prop(inst,'Footprint')[2]=Q(footprint)
    if xy:c['x'],c['y']=xy;c['angle']=angle
    path.write_text(dump(sch)+'\n')
def n(d):return {str(k):v for k,v in d.items()}
update('U3',n({1:'VSYS',2:'VBAT',3:None,4:'CHG_CE_N',5:'GND',6:'BAT_TS',7:'I2C_SDA',8:'I2C_SCL',9:None,10:'USB_PROTECTED',11:'GND'}),'BQ25186DLHR',xy=(121,61),angle=90)
update('J1',n({1:'BAT_PACK_POS',2:'GND'}))
update('R6',n({1:'VSYS',2:'CHG_CE_N'}),'100k',xy=(116.5,60.5))
update('R7',n({1:'CHG_ENABLE',2:'GND'}),'4.7k',xy=(111.5,66))
update('R8',n({1:'USB_AON_3V3',2:'USB_CC_HIGH_N'}),'100k',xy=(119,61.8))
update('R9',n({1:'USB_FUSED',2:'USB_VBUS_DET'}),'887k 1%',xy=(124,59))
update('C5',n({1:'USB_PROTECTED',2:'GND'}),'2.2uF 25V X7R',
       'Capacitor_SMD:C_0805_2012Metric',xy=(124,58),angle=90)
update('C6',value='10uF 25V X5R',xy=(124,63.5))
update('C7',value='4.7uF 10V X7R',footprint='Capacitor_SMD:C_0603_1608Metric',xy=(118.8,64.5))

subprocess.run(['kicad-cli','sch','export','netlist',str(OUT/'handset.kicad_sch'),'--format','kicadxml','-o',str(OUT/'netlist.xml')],check=True)
nc={}
for net in ET.parse(OUT/'netlist.xml').findall('./nets/net'):
    if net.get('name').startswith('unconnected-('):
        for node in net.findall('node'):nc[(node.get('ref'),node.get('pin'))]=net.get('name')

b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
changed=['U3','J1','R6','R7','R8','R9','C5','C6','C7']
for ref in changed:
    c=byref[ref];f=fps[ref]
    assert not any(b.GetConnectivity().GetConnectedTracks(pad) for pad in f.Pads()),ref+' already routed'
    lib,part=c['footprint'].split(':')
    if str(f.GetFPID().GetLibItemName())!=part:
        new=p.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',part)
        path=f.GetPath();b.Remove(f);f.thisown=False;f=new;b.Add(f)
        f.SetPath(path);f.SetReference(ref);f.SetFPID(p.LIB_ID(lib,part))
        if c['side']=='B':f.Flip(f.GetPosition(),False)
    f.SetValue(c['value']);f.Value().SetVisible(False)
    f.SetPosition(p.VECTOR2I(p.FromMM(c['x']),p.FromMM(c['y'])));f.SetOrientationDegrees(c.get('angle',0))
    for pad in f.Pads():
        net=c['nets'].get(pad.GetNumber())
        if net:
            ni=b.FindNet(net)
            if not ni:ni=p.NETINFO_ITEM(b,net);b.Add(ni)
            pad.SetNet(ni)
        else:pad.SetNetCode(0)
for f in b.GetFootprints():
    if f.GetReference() in changed+[c['ref'] for c in entries]:
        f.Reference().SetLayer(p.B_Fab if f.GetLayer()==p.B_Cu else p.F_Fab)
    for pad in f.Pads():
        name=nc.get((f.GetReference(),pad.GetNumber()))
        if name:
            ni=b.FindNet(name)
            if not ni:ni=p.NETINFO_ITEM(b,name);b.Add(ni)
            pad.SetNet(ni)
p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
shutil.copy2(OUT/'handset.kicad_pcb',OUT/'power-entry-unrouted.kicad_pcb')
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
(OUT/'power-entry-update.json').write_text(json.dumps({
    'source_sha256':hashlib.sha256((SOURCE/'handset.kicad_pcb').read_bytes()).hexdigest(),
    'added_refs':[c['ref'] for c in entries], 'changed_refs':changed,
    'scope':'Protected USB input and programmable battery charger; not a manufacturing release',
    'fabrication_released':False},indent=2)+'\n')
print(OUT)
