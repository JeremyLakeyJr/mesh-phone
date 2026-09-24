#!/usr/bin/env python3
"""One-shot, additive population of verified handset blocks; preserve saved layout.

References and remaining release conditions: hardware/handset-rev-a/population-review.md.
Never invokes the original generator. Snapshot before any project mutation.
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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'hardware/handset-rev-a/generated'
marker = OUT/'population-update.json'
if marker.exists():
    raise SystemExit('Already applied; edit the saved project, do not reset placements.')
boardpath = OUT/'handset.kicad_pcb'
digest = hashlib.sha256(boardpath.read_bytes()).hexdigest()
snapshot = ROOT/'archive/handset-before-population'/digest[:12]
snapshot.mkdir(parents=True, exist_ok=True)
for f in OUT.iterdir():
    if f.suffix in ('.kicad_pcb', '.kicad_sch', '.kicad_pro', '.json', '.csv'):
        if not (snapshot/f.name).exists():
            shutil.copy2(f, snapshot/f.name)
p.SwigPyIterator.next = p.SwigPyIterator.__next__
b = p.LoadBoard(str(boardpath))
spec = json.loads((OUT/'connectivity.json').read_text())
fps = {f.GetReference(): f for f in b.GetFootprints()}
uid = lambda s: str(uuid.uuid5(uuid.NAMESPACE_URL, 'handset-population/'+s))
v = lambda x,y: p.VECTOR2I(p.FromMM(x),p.FromMM(y))
symbols = {}
additions = []

def symbol(libid):
    if libid in symbols:
        return copy.deepcopy(symbols[libid])
    lib,name = libid.split(':')
    data = parse(Path('/usr/share/kicad/symbols',lib+'.kicad_sym').read_text())
    original = next(s for s in children(data,'symbol') if s[1] == name)
    s = copy.deepcopy(original)
    ext = child(s,'extends')
    if ext:
        parent = symbol(lib+':'+ext[1])
        for item in children(parent,'symbol'):
            part = copy.deepcopy(item)
            part[1] = Q(name+'_'+str(part[1]).split('_')[-2]+'_'+str(part[1]).split('_')[-1])
            s.append(part)
        s.remove(ext)
    s[1] = Q(libid)
    symbols[libid] = s
    return copy.deepcopy(s)

def custom(name, pins):
    height = (math.ceil(len(pins)/2)+1)*2.54
    s = parse(f'''(symbol "Handset:{name}" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "{name}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
      (symbol "{name}_0_1" (rectangle (start -10.16 {height/2}) (end 10.16 {-height/2})
       (stroke (width 0.254) (type default)) (fill (type background)))))''')
    unit = ['symbol',Q(name+'_1_1')]
    for i,(num,label,typ) in enumerate(pins):
        right = i >= math.ceil(len(pins)/2)
        j = i-math.ceil(len(pins)/2) if right else i
        y = height/2-2.54*(j+1)
        unit.append(parse(f'''(pin {typ} line (at {15.24 if right else -15.24} {y} {180 if right else 0})
         (length 5.08) (name "{label}" (effects (font (size 1 1))))
         (number "{num}" (effects (font (size 1 1)))))'''))
    s.append(unit)
    symbols['Handset:'+name] = s
    return 'Handset:'+name

def add(ref,value,libid,fp,nets,x,y,sheet,side='B',angle=0):
    assert ref not in fps and ref not in [c['ref'] for c in additions], ref
    additions.append(dict(ref=ref,value=value,libid=libid,footprint=fp,
        nets={str(k):n for k,n in nets.items()},x=x,y=y,side=side,angle=angle,sheet=sheet))

def passive(ref,value,nets,x,y,sheet,size='0402',side='B',angle=0):
    kind = ref[0]
    lib = {'R':'Resistor','C':'Capacitor','L':'Inductor'}[kind]
    dims = {'0402':'1005','0603':'1608','0805':'2012'}[size]
    add(ref,value,'Device:'+kind,f'{lib}_SMD:{kind}_{size}_{dims}Metric',dict(enumerate(nets,1)),x,y,sheet,side,angle)

def conn(ref,value,nets,x,y,sheet):
    count=len(nets)
    add(ref,value,f'Connector_Generic:Conn_01x{count:02}',
        f'Connector_JST:JST_GH_BM{count:02}B-GHS-TBT_1x{count:02}-1MP_P1.25mm_Vertical',
        dict(enumerate(nets,1)),x,y,sheet)

# ST DS13541 table 2: QFN32, not the incompatible WLCSP numbering.
names = ['VDD_IO','TAD1','VDD_D','XTO','XTI','GND_D','VDD_A','VDD','VDD_RF','VDD_TX',
 'VDD_AM','GND_DR1','RFO1','VDD_DR','RFO2','GND_DR2','EXT_LM','AAT_A','AAT_B','I2C_EN',
 'VSS','RFI1','RFI2','AGDC','TAD2','GND_A','IRQ','MCU_CLK','BSS','SCLK','MOSI','MISO','EP']
power={1,6,8,10,12,14,16,21,26,33}
outputs={2,3,4,7,9,11,13,15,17,18,19,27,28}
nfc=custom('ST25R3916B_AQET',[(i,n,'power_in' if i in power else 'output' if i in outputs else 'tri_state' if i==32 else 'input' if i in (5,20,22,23,29,30,31) else 'passive') for i,n in enumerate(names,1)])
add('U13','ST25R3916B-AQET',nfc,'Package_DFN_QFN:VQFN-32-1EP_5x5mm_P0.5mm_EP3.5x3.5mm',
 {1:'+3V3',2:None,3:'NFC_VDD_D',4:'NFC_XTO',5:'NFC_XTI',6:'GND',7:'NFC_VDD_A',8:'+3V3',
  9:'NFC_VDD_RF',10:'+3V3',11:'NFC_VDD_AM',12:'GND',13:'NFC_RFO1',14:'NFC_VDD_RF',15:'NFC_RFO2',
  16:'GND',17:None,18:None,19:None,20:'GND',21:'GND',22:'NFC_RFI1',23:'NFC_RFI2',24:'NFC_AGDC',
  25:None,26:'GND',27:'NFC_IRQ',28:None,29:'NFC_CS',30:'SPI_SCK',31:'SPI_MOSI',32:'SPI_MISO',33:'GND'},121,80,'nfc')
for ref,value,net,x,y in [('C31','100nF','+3V3',117,76),('C32','2.2uF','NFC_VDD_D',117,79),
 ('C33','2.2uF','NFC_VDD_A',117,82),('C34','2.2uF','NFC_VDD_RF',121,85),
 ('C35','2.2uF','NFC_VDD_AM',124,85),('C36','10nF','NFC_AGDC',128,81),
 ('C37','1uF','+3V3',128,78)]:
    passive(ref,value,[net,'GND'],x,y,'nfc',size='0603' if value=='2.2uF' else '0402')
passive('R40','10k',['+3V3','NFC_CS'],125,74,'nfc')
add('Y1','ABM8-27.120MHZ-B2-T','Device:Crystal_GND24','Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',
 {1:'NFC_XTI',2:'GND',3:'NFC_XTO',4:'GND'},121,75,'nfc')
passive('C38','27pF C0G',['NFC_XTI','GND'],118,73,'nfc')
passive('C39','27pF C0G',['NFC_XTO','GND'],121,72,'nfc')
# Matching is not guessed: these raw analog nets remain explicit release blockers.

# TPS2553 SOT23 pinout, SLVS841F p5. 100k limits accessory current conservatively.
sw=custom('TPS2553DBVR',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),
 (4,'FAULT_N','open_collector'),(5,'ILIM','passive'),(6,'OUT','power_out')])
add('U14','TPS2553DBVR',sw,'Package_TO_SOT_SMD:SOT-23-6',
 {1:'+3V3',2:'GND',3:'+3V3',4:'EXP_FAULT_N',5:'EXP_ILIM',6:'EXP_3V3'},78,99,'protection')
passive('R41','100k 1%',['EXP_ILIM','GND'],75,97,'protection')
passive('R42','100k',['+3V3','EXP_FAULT_N'],75,100,'protection')
passive('C40','100nF',['+3V3','GND'],81,97,'protection')
passive('C41','10uF',['EXP_3V3','GND'],81,100,'protection',size='0805')
for ref,x,nets in [('U15',89,['EXP_SCL','EXP_SDA','EXP_SCK','EXP_MOSI']),
                   ('U16',93,['EXP_MISO','EXP_CS_PORT','EXP_IRQ_PORT',None])]:
    add(ref,'TPD4E05U06DQAR','Power_Protection:TPD4E05U06DQA','Package_SON:USON-10_2.5x1.0mm_P0.5mm',
        {1:nets[0],2:nets[1],3:'GND',4:nets[2],5:nets[3],6:None,7:None,8:'GND',9:None,10:None},x,75,'protection')
add('U17','TPD4E05U06DQAR','Power_Protection:TPD4E05U06DQA','Package_SON:USON-10_2.5x1.0mm_P0.5mm',
 {1:'USB_D_P',2:'USB_D_N',3:'GND',4:'USB_CC1',5:'USB_CC2',6:None,7:None,8:'GND',9:None,10:None},121,53,'protection',side='F')

# Hirose's published contact order and standard KiCad land pattern.
add('J23','DM3D-SF','Connector:Micro_SD_Card_Det2','Connector_Card:microSD_HC_Hirose_DM3D-SF',
 {1:'SD_DAT2',2:'SD_CS',3:'SPI_MOSI',4:'+3V3',5:'SPI_SCK',6:'GND',7:'SPI_MISO',8:'SD_DAT1',9:None,10:None,'SH':'GND'},123,99,'storage-ir',side='F',angle=90)
for ref,net,x in [('R43','SD_DAT2',116),('R44','SD_CS',119),('R45','SD_DAT1',122)]:
    passive(ref,'47k',['+3V3',net],x,89,'storage-ir',side='F')
passive('C42','100nF',['+3V3','GND'],126,89,'storage-ir',side='F')
passive('C43','10uF',['+3V3','GND'],129,89,'storage-ir',side='F',size='0805')

# IR optics are case-mounted, connected by actual JST GH footprints.
add('Q1','AO3400A','Transistor_FET:AO3400A','Package_TO_SOT_SMD:SOT-23',
 {1:'IR_GATE',2:'GND',3:'IR_LED_K'},96,35,'storage-ir')
passive('R46','100',['IR_TX','IR_GATE'],93,38,'storage-ir')
passive('R47','100k',['IR_GATE','GND'],96,38,'storage-ir')
passive('R48','47 1% 0.125W',['+3V3','IR_LED_A'],93,32,'storage-ir',size='0805')
conn('J24','TSAL6400_CASE_LED',['IR_LED_A','IR_LED_K'],81,34,'storage-ir')
conn('J25','TSOP38438_CASE_RX',['IR_RX','GND','IR_RX_VCC'],103,35,'storage-ir')
passive('R49','100',['+3V3','IR_RX_VCC'],106,39,'storage-ir')
passive('C44','1uF',['IR_RX_VCC','GND'],106,42,'storage-ir')

# LF translation is now physical. Dedicated host timing input still needs allocation.
ahct=custom('SN74AHCT125PW',[(i,n,'power_in' if i in (7,14) else 'tri_state' if i in (3,6,8,11) else 'input')
 for i,n in enumerate(['OE1_N','A1','Y1','OE2_N','A2','Y2','GND','Y3','A3','OE3_N','Y4','A4','OE4_N','VCC'],1)])
add('U18','SN74AHCT125PWR',ahct,'Package_SO:TSSOP-14_4.4x5mm_P0.65mm',
 {1:'GND',2:'RFID_CLK',3:'LF_CLK_5V',4:'GND',5:'RFID_DIN',6:'LF_DIN_5V',7:'GND',
  8:None,9:'GND',10:'+5V_RF',11:None,12:'GND',13:'+5V_RF',14:'+5V_RF'},82,130,'lf-support')
add('U19','SN74LVC1G17DBVR','74xGxx:74LVC1G17','Package_TO_SOT_SMD:SOT-23-5',
 {1:None,2:'LF_DOUT_5V',3:'GND',4:'RFID_DOUT_3V3',5:'+3V3'},82,136,'lf-support')
passive('C45','100nF',['+5V_RF','GND'],87,130,'lf-support')
passive('C46','100nF',['+3V3','GND'],86,136,'lf-support')
passive('R50','100k',['RFID_CLK','GND'],88,133,'lf-support')
passive('R51','100k',['RFID_DIN','GND'],88,136,'lf-support')

# Correct known placement collisions, without touching key routes or unrelated parts.
moves={'C3':(98,68,0),'J3':(88,35,0),'J5':(102,46,0),'J8':(101,52,0),
 'J20':(118.5,33.5,0),'J21':(129,43,0),'U6':(78,84,0),'C13':(82,83,0),
 'C14':(73,86,0),'R13':(82,86,0),'SW19':(70,93,90),'J2':(126,68,0)}
before={}
for ref,(x,y,a) in moves.items():
    fp=fps[ref];pos=fp.GetPosition()
    before[ref]=[p.ToMM(pos.x),p.ToMM(pos.y),fp.GetOrientationDegrees()]
    fp.SetPosition(v(x,y));fp.SetOrientationDegrees(a)

root=parse((snapshot/'handset.kicad_sch').read_text())
rootid=child(root,'uuid')[1]
for index,sheet in enumerate(dict.fromkeys(c['sheet'] for c in additions)):
    sid=uid(sheet)
    sch=parse(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{sid}") (paper "A2") (lib_symbols))')
    seen=set()
    for i,c in enumerate(x for x in additions if x['sheet']==sheet):
        ref=c['ref'];s=symbol(c['libid']);sx=63.5+(i%4)*132.08;sy=63.5+(i//4)*76.2
        if c['libid'] not in seen:
            child(sch,'lib_symbols').append(s);seen.add(c['libid'])
        inst=parse(f'''(symbol (lib_id "{c['libid']}") (at {sx} {sy} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}")
          (property "Reference" "{ref}" (at {sx} {sy-27.94} 0) (effects (font (size 1.27 1.27))))
          (property "Value" "{c['value']}" (at {sx} {sy-25.4} 0) (effects (font (size 1.27 1.27))))
          (property "Footprint" "{c['footprint']}" (at {sx} {sy} 0) (effects (font (size 1.27 1.27)) (hide yes)))
          (instances (project "handset" (path "/{rootid}/{sid}" (reference "{ref}") (unit 1)))))''')
        for unit in children(s,'symbol'):
            for pin in children(unit,'pin'):
                num=str(child(pin,'number')[1]);at=child(pin,'at')
                px=sx+float(at[1]);py=sy-float(at[2]);a=float(at[3]);net=c['nets'].get(num)
                inst.append(parse(f'(pin "{num}" (uuid "{uid(ref+num)}"))'))
                if net:
                    ex=round(px-5.08*math.cos(math.radians(a)),6);ey=round(py+5.08*math.sin(math.radians(a)),6)
                    sch.append(parse(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+num+"w")}"))'))
                    sch.append(parse(f'(global_label "{net}" (shape input) (at {ex} {ey} {a}) (effects (font (size 1 1)) (justify left)) (uuid "{uid(ref+num+"l")}"))'))
                else:
                    sch.append(parse(f'(no_connect (at {px} {py}) (uuid "{uid(ref+num+"nc")}"))'))
        sch.append(inst)
        lib,name=c['footprint'].split(':')
        fp=p.FootprintLoad('/usr/share/kicad/footprints/'+lib+'.pretty',name)
        if not fp:raise ValueError(c['footprint'])
        fp.SetReference(ref);fp.SetValue(c['value']);fp.SetFPID(p.LIB_ID(lib,name));b.Add(fp)
        fp.SetPosition(v(c['x'],c['y']))
        if c['side']=='B':fp.Flip(fp.GetPosition(),False)
        fp.SetOrientationDegrees(c['angle'])
        path=p.KIID_PATH()
        for ident in (str(rootid),sid,uid(ref)):path.push_back(p.KIID(ident))
        fp.SetPath(path);fp.Reference().SetTextSize(v(.7,.7));fp.Reference().SetTextThickness(p.FromMM(.12));fp.Value().SetVisible(False)
        for pad in fp.Pads():
            net=c['nets'].get(pad.GetNumber())
            if net:
                n=b.FindNet(net)
                if not n:n=p.NETINFO_ITEM(b,net);b.Add(n)
                pad.SetNet(n)
        fps[ref]=fp
    (OUT/(sheet+'.kicad_sch')).write_text(dump(sch)+'\n')
    rx=135+(index%2)*95;ry=190+(index//2)*45
    root.append(parse(f'''(sheet (at {rx} {ry}) (size 90 35) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sid}")
     (property "Sheetname" "{sheet}" (at {rx} {ry-1} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
     (property "Sheetfile" "{sheet}.kicad_sch" (at {rx} {ry+36} 0) (effects (font (size 1.27 1.27)) (justify left top)))
     (instances (project "handset" (path "/{rootid}" (page "{9+index}")))))'''))
(OUT/'handset.kicad_sch').write_text(dump(root)+'\n')
# Save reusable custom symbols, retaining previous library content.
libpath=OUT/'Handset.kicad_sym'
libroot=parse(libpath.read_text())
for libid,s in symbols.items():
    if libid.startswith('Handset:'):
        entry=copy.deepcopy(s);entry[1]=Q(libid.split(':')[1])
        for old in children(libroot,'symbol'):
            if old[1]==entry[1]:libroot.remove(old)
        libroot.append(entry)
libpath.write_text(dump(libroot)+'\n')

reservations=json.loads((snapshot/'reservations.json').read_text())
removed=[r for r in reservations if r[0].startswith(('NFC ','LF timing','IR TX','microSD ','J16 load'))]
for item in list(b.GetDrawings()):
    for label,x,y,w,h,side in removed:
        layer=p.User_1 if side=='B' else p.User_2
        if item.GetLayer()!=layer:continue
        if isinstance(item,p.PCB_TEXT) and label in item.GetText():b.Remove(item);break
        if isinstance(item,p.PCB_SHAPE):
            pts=[item.GetStart(),item.GetEnd()]
            if all(x-w/2-.01<=p.ToMM(pt.x)<=x+w/2+.01 and y-h/2-.01<=p.ToMM(pt.y)<=y+h/2+.01 for pt in pts):
                b.Remove(item);break
(OUT/'reservations.json').write_text(json.dumps([r for r in reservations if r not in removed],indent=2)+'\n')
spec.extend(additions)
for c in spec:
    if c['ref'] in moves:
        x,y,a=moves[c['ref']];c.update(x=x,y=y,angle=a)
p.SaveBoard(str(boardpath),b)
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
marker.write_text(json.dumps({'snapshot':str(snapshot.relative_to(ROOT)),'added':[c['ref'] for c in additions],
 'moved_before':before,'moved_after':moves,'removed_reservations':[r[0] for r in removed]},indent=2)+'\n')
print(f'Added {len(additions)} physical components with schematic pin nets; saved snapshot {snapshot}')
