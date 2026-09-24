#!/usr/bin/env python3
"""Populate the case-mounted ER-TFT024IPS-3 interface on the saved PCB."""
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

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hardware/handset-rev-a/generated'
if (OUT/'display-update.json').exists():raise SystemExit('Already applied; preserve saved PCB edits.')
snapshot=ROOT/'archive/handset-before-display'/hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest()[:12]
snapshot.mkdir(parents=True,exist_ok=True)
for f in OUT.iterdir():
    if f.suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.json','.csv') and not (snapshot/f.name).exists():shutil.copy2(f,snapshot/f.name)
p.SwigPyIterator.next=p.SwigPyIterator.__next__
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));spec=json.loads((OUT/'connectivity.json').read_text())
uid=lambda s:str(uuid.uuid5(uuid.NAMESPACE_URL,'handset-display/'+s))
v=lambda x,y:p.VECTOR2I(p.FromMM(x),p.FromMM(y))
# FH12 catalog p10 explicitly shares the top/bottom-contact PCB land pattern.
# Preserve those lands, replace the body/courtyard for the larger top-contact body.
fpname='FH12A-50S-0.5SH_TopContact'
fpdata=parse(Path('/usr/share/kicad/footprints/Connector_FFC-FPC.pretty/Hirose_FH12-50S-0.5SH_1x50-1MP_P0.50mm_Horizontal.kicad_mod').read_text())
fpdata[1]=Q(fpname);prop(fpdata,'Value')[2]=Q(fpname)
fpdata[:]=[e for e in fpdata if not isinstance(e,list) or e[0] not in ('fp_line','fp_rect','fp_text','model')]
for layer,x1,y1,x2,y2 in [('F.Fab',-14.75,-1.2,14.75,5.8),('F.CrtYd',-15.55,-3,15.55,6.3)]:
    fpdata.append(parse(f'(fp_rect (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.05) (type solid)) (fill none) (layer "{layer}"))'))
child(fpdata,'descr')[1]=Q('FH12A-50S-0.5SH(55) top contact; shared PCB lands per Hirose FH12 catalog p10; actuator and cable clearance require mechanical review.')
(OUT/'Handset.pretty'/(fpname+'.kicad_mod')).write_text(dump(fpdata)+'\n')

entries=[]
def add(ref,value,libid,footprint,nets,x,y,side='F'):
    entries.append(dict(ref=ref,value=value,libid=libid,footprint=footprint,nets={str(k):n for k,n in nets.items()},x=x,y=y,side=side,angle=0,sheet='display'))
def passive(ref,value,a,z,x,y,size='0402'):
    kind=ref[0];lib='Resistor' if kind=='R' else 'Capacitor';dims={'0402':'1005','0603':'1608','0805':'2012'}[size]
    add(ref,value,'Device:'+kind,f'{lib}_SMD:{kind}_{size}_{dims}Metric',{1:a,2:z},x,y)
# Four-wire SPI interface II, IM[3:0]=1110. Parallel/RGB inputs held low.
nets={i:'GND' for i in range(1,51)}
nets.update({1:'+5V_RF',2:'LCD_K1',3:'LCD_K2',4:'LCD_K3',5:'LCD_K4',6:'GND',7:'+3V3',8:'+3V3',9:'+3V3',
 10:'LCD_RESET',33:'SPI_MISO',34:'SPI_MOSI',35:'+3V3',36:'LCD_DC',37:'SPI_SCK',38:'LCD_CS',39:None,
 40:'+3V3',41:'+3V3',42:'+3V3',44:'I2C_SCL',45:'I2C_SDA',46:'TOUCH_IRQ',47:'TOUCH_RESET'})
add('J26','FH12A-50S-0.5SH(55)','Connector_Generic:Conn_01x50','Handset:'+fpname,nets,100,65)
for i in range(4):passive('R'+str(52+i),'150 1% 0.1W','LCD_K'+str(i+1),'LCD_LED_RETURN',91+i*3,74,'0603')
add('Q2','AO3400A','Transistor_FET:Q_NMOS_GSD','Package_TO_SOT_SMD:SOT-23',{1:'LCD_BL_GATE',2:'GND',3:'LCD_LED_RETURN'},107,74)
passive('R56','100','LCD_BL_EN','LCD_BL_GATE',111,74)
passive('R57','100k','LCD_BL_GATE','GND',111,77)
passive('R58','10k','+3V3','LCD_CS',85,62)
passive('C47','100nF','+3V3','GND',116,65)
passive('C48','4.7uF','+3V3','GND',116,68,'0603')
passive('C49','10uF','+5V_RF','GND',116,72,'0805')
passive('R59','10k','+3V3','IR_RX',100,60)

root=parse((OUT/'handset.kicad_sch').read_text());rootid=child(root,'uuid')[1];sid=uid('display')
sch=parse(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{sid}") (paper "A2") (lib_symbols))')
seen=set()
for i,c in enumerate(entries):
    lib,name=c['libid'].split(':');s=copy.deepcopy(next(s for s in children(parse(Path('/usr/share/kicad/symbols',lib+'.kicad_sym').read_text()),'symbol') if s[1]==name))
    s[1]=Q(c['libid']);assert child(s,'extends') is None
    if c['libid'] not in seen:child(sch,'lib_symbols').append(s);seen.add(c['libid'])
    sx=63.5+(i%4)*132.08;sy=101.6+(i//4)*76.2;ref=c['ref']
    inst=parse(f'''(symbol (lib_id "{c['libid']}") (at {sx} {sy} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}")
      (property "Reference" "{ref}" (at {sx} {sy-20} 0) (effects (font (size 1.27 1.27))))
      (property "Value" "{c['value']}" (at {sx} {sy-17.46} 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "{c['footprint']}" (at {sx} {sy} 0) (effects (font (size 1.27 1.27)) (hide yes)))
      (instances (project "handset" (path "/{rootid}/{sid}" (reference "{ref}") (unit 1)))))''')
    for unit in children(s,'symbol'):
        for pin in children(unit,'pin'):
            num=str(child(pin,'number')[1]);at=child(pin,'at');px=sx+float(at[1]);py=sy-float(at[2]);a=float(at[3]);net=c['nets'].get(num)
            inst.append(parse(f'(pin "{num}" (uuid "{uid(ref+num)}"))'))
            if net:
                ex=round(px-5.08*math.cos(math.radians(a)),6);ey=round(py+5.08*math.sin(math.radians(a)),6)
                sch.append(parse(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+num+"w")}"))'))
                sch.append(parse(f'(global_label "{net}" (shape input) (at {ex} {ey} {a}) (effects (font (size 1 1)) (justify left)) (uuid "{uid(ref+num+"l")}"))'))
            else:sch.append(parse(f'(no_connect (at {px} {py}) (uuid "{uid(ref+num+"nc")}"))'))
    sch.append(inst)
    lib,name=c['footprint'].split(':');fp=p.FootprintLoad(str(OUT/'Handset.pretty') if lib=='Handset' else '/usr/share/kicad/footprints/'+lib+'.pretty',name)
    fp.SetReference(ref);fp.SetValue(c['value']);fp.SetFPID(p.LIB_ID(lib,name));b.Add(fp);fp.SetPosition(v(c['x'],c['y']))
    path=p.KIID_PATH()
    for ident in (str(rootid),sid,uid(ref)):path.push_back(p.KIID(ident))
    fp.SetPath(path);fp.Value().SetVisible(False)
    for pad in fp.Pads():
        net=c['nets'].get(pad.GetNumber())
        if net:
            n=b.FindNet(net)
            if not n:n=p.NETINFO_ITEM(b,net);b.Add(n)
            pad.SetNet(n)
# Reassign IR receive to a real ESP32 timing-capable input; scanner output enables backlight.
for sheet,ref,pin,net in [('keys','U2','14','LCD_BL_EN'),('core','U1','15','IR_RX')]:
    path=OUT/(sheet+'.kicad_sch');data=parse(path.read_text())
    inst=next(s for s in children(data,'symbol') if prop(s,'Reference')[2]==ref)
    libid=child(inst,'lib_id')[1];s=next(s for s in children(child(data,'lib_symbols'),'symbol') if s[1]==libid)
    sympin=next(pn for u in children(s,'symbol') for pn in children(u,'pin') if str(child(pn,'number')[1])==pin)
    at=child(sympin,'at');where=child(inst,'at');px=float(where[1])+float(at[1]);py=float(where[2])-float(at[2]);a=float(at[3])
    if ref=='U2':
        label=next(g for g in children(data,'global_label') if g[1]=='IR_RX');label[1]=Q(net)
    else:
        nc=next(n for n in children(data,'no_connect') if abs(float(child(n,'at')[1])-px)<.001 and abs(float(child(n,'at')[2])-py)<.001);data.remove(nc)
        ex=round(px-5.08*math.cos(math.radians(a)),6);ey=round(py+5.08*math.sin(math.radians(a)),6)
        data.append(parse(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(ref+pin+"w")}"))'))
        data.append(parse(f'(global_label "{net}" (shape input) (at {ex} {ey} {a}) (effects (font (size 1 1)) (justify left)) (uuid "{uid(ref+pin+"l")}"))'))
    path.write_text(dump(data)+'\n')
    for c in spec:
        if c['ref']==ref:c['nets'][pin]=net
    for f in b.GetFootprints():
        if f.GetReference()==ref:
            for pad in f.Pads():
                if pad.GetNumber()==pin:pad.SetNet(b.FindNet(net))
child(root,'paper')[1]=Q('A2')
root.append(parse(f'''(sheet (at 325 190) (size 90 35) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0)) (uuid "{sid}")
 (property "Sheetname" "display" (at 325 189 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "display.kicad_sch" (at 325 226 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project "handset" (path "/{rootid}" (page "13")))))'''))
(OUT/'handset.kicad_sch').write_text(dump(root)+'\n');(OUT/'display.kicad_sch').write_text(dump(sch)+'\n')
reservations=json.loads((OUT/'reservations.json').read_text())
(OUT/'reservations.json').write_text(json.dumps([r for r in reservations if not r[0].startswith('LCD FPC')],indent=2)+'\n')
spec.extend(entries);p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
pcbdata=parse((OUT/'handset.kicad_pcb').read_text())
for item in list(pcbdata):
    if not isinstance(item,list):continue
    if item[0]=='gr_text' and 'LCD FPC ordering code TBD' in str(item[1]):pcbdata.remove(item)
    elif item[0]=='gr_line' and child(item,'layer')[1]=='User.2':
        if all(89.99<=float(pt[1])<=110.01 and 63.99<=float(pt[2])<=70.01 for pt in (child(item,'start'),child(item,'end'))):pcbdata.remove(item)
(OUT/'handset.kicad_pcb').write_text(dump(pcbdata)+'\n')
(OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
with (OUT/'placement.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
(OUT/'display-update.json').write_text(json.dumps({'snapshot':str(snapshot.relative_to(ROOT)),'added':[c['ref'] for c in entries]},indent=2)+'\n')
print('Added display connector, backlight switch and supporting passives; IR RX moved to GPIO3.')
