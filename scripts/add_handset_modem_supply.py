#!/usr/bin/env python3
"""Populate modem power; explicitly requires burst/UVLO and footprint review."""
import hashlib
import json
import shutil
from handset_additive import ROOT,OUT,add_sheet
from cad_sexpr import Q,parse,dump,child,children

marker=OUT/'modem-supply-update.json'
if marker.exists():raise SystemExit('Already applied; preserve saved layout.')
snapshot=ROOT/'archive/handset-before-modem-supply'/hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest()[:12]
snapshot.mkdir(parents=True,exist_ok=True)
for f in OUT.iterdir():
    if f.suffix in ('.kicad_pcb','.kicad_sch','.json','.csv') and not (snapshot/f.name).exists():shutil.copy2(f,snapshot/f.name)

def footprint(name,body,court,pads,description):
    f=parse(f'''(footprint "{name}" (version 20250108) (generator "pcbnew") (layer "F.Cu") (attr smd)
     (descr "{description}")
     (property "Reference" "REF**" (at 0 -3 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
     (property "Value" "{name}" (at 0 3 0) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12)))))''')
    for layer,wh in [('F.Fab',body),('F.CrtYd',court)]:
        w,h=wh;f.append(parse(f'(fp_rect (start {-w/2} {-h/2}) (end {w/2} {h/2}) (stroke (width 0.05) (type solid)) (fill none) (layer "{layer}"))'))
    for num,x,y,w,h,defined in pads:
        layers='"F.Cu"' if defined=='bridge' else '"F.Cu" "F.Paste" "F.Mask"'
        extras='(solder_mask_margin -0.05) (solder_paste_margin_ratio -0.04)' if defined is True else ''
        f.append(parse(f'(pad "{num}" smd roundrect (at {x} {y}) (size {w} {h}) (layers {layers}) (roundrect_rratio 0.1) {extras})'))
    (OUT/'Handset.pretty'/(name+'.kicad_mod')).write_text(dump(f)+'\n')

# TI RNM0015A drawing 4222000/B: asymmetric signal and power lands.
pads=[(i,-1.15,-.75+(i-1)*.5,.6,.25,False) for i in range(1,5)]
pads += [(5,-.725,1.4,.25,.6,False),(6,-.225,1.4,.25,.6,False),
 (7,.275,1.4,.35,.7,True),(8,.775,1.4,.35,.7,True),
 (9,.775,.5,1.45,.35,True),(10,.6,0,1.8,.35,True),(11,.775,-.5,1.45,.35,True),
 (12,.775,-1.4,.35,.7,True),(13,.275,-1.4,.35,.7,True),
 (14,-.225,-1.4,.25,.6,False),(15,-.725,-1.4,.25,.6,False),
 (7,.525,1.225,.85,.35,'bridge'),(12,.525,-1.225,.85,.35,'bridge')]
footprint('TPS63070_RNM0015A',(2.5,3),(3.5,4),pads,'TI TPS63070 RNM0015A; drawing 4222000/B. Solder-mask-defined power lands. Independent pre-fab land and stencil review required.')
footprint('Coilcraft_XFL4020',(4.3,4.3),(4.8,4.8),[(1,-1.185,0,.98,3.4,False),(2,1.185,0,.98,3.4,False)],'Coilcraft XFL4020 recommended land pattern, document 745-3, 2026-03-10; 2.1mm maximum height.')

names=['PS_SYNC','PG','VAUX','GND','FB','FB2','VOUT','VOUT','L2','PGND','L1','VIN','VIN','EN','VSEL']
s=parse('''(symbol "Handset:TPS63070RNM" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)
 (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
 (property "Value" "TPS63070RNM" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
 (symbol "TPS63070RNM_0_1" (rectangle (start -10.16 12.7) (end 10.16 -12.7) (stroke (width 0.254) (type default)) (fill (type background)))))''')
u=['symbol',Q('TPS63070RNM_1_1')]
for i,name in enumerate(names,1):
    right=i>8;j=i-9 if right else i-1;y=10.16-j*2.54
    typ='power_in' if i in (4,10,12,13) else 'power_out' if i in (3,7,8) else 'open_collector' if i==2 else 'input' if i in (1,5,14,15) else 'passive'
    u.append(parse(f'(pin {typ} line (at {15.24 if right else -15.24} {y} {180 if right else 0}) (length 5.08) (name "{name}" (effects (font (size 1 1)))) (number "{i}" (effects (font (size 1 1)))))'))
s.append(u)
entries=[]
def add(ref,value,libid,fp,nets,x,y):entries.append(dict(ref=ref,value=value,libid=libid,footprint=fp,nets=nets,x=x,y=y,side='F',angle=0))
def passive(ref,value,a,z,x,y,size='0402'):
    kind=ref[0];lib={'R':'Resistor','C':'Capacitor'}[kind];dims={'0402':'1005','0603':'1608','0805':'2012'}[size]
    add(ref,value,'Device:'+kind,f'{lib}_SMD:{kind}_{size}_{dims}Metric',{1:a,2:z},x,y)
add('U20','TPS63070RNMR','Handset:TPS63070RNM','Handset:TPS63070_RNM0015A',
 {1:'GND',2:None,3:'MODEM_VAUX',4:'GND',5:'MODEM_FB',6:None,7:'MODEM_SUPPLY',8:'MODEM_SUPPLY',
 9:'MODEM_L2',10:'GND',11:'MODEM_L1',12:'VBAT',13:'VBAT',14:'MODEM_REG_EN',15:'GND'},98,45)
add('L4','XFL4020-152MEC / 1.5uH','Device:L','Handset:Coilcraft_XFL4020',{1:'MODEM_L1',2:'MODEM_L2'},103,45)
for ref,value,net,x,y,size in [('C50','10uF 10V X7R','VBAT',95,42,'0805'),('C51','10uF 10V X7R','VBAT',99,41,'0805'),
 ('C52','22uF 10V X5R','MODEM_SUPPLY',102,50,'0805'),('C53','22uF 10V X5R','MODEM_SUPPLY',106,50,'0805'),
 ('C54','22uF 10V X5R','MODEM_SUPPLY',110,50,'0805'),('C55','100nF','MODEM_VAUX',94,45,'0402')]:
    passive(ref,value,net,'GND',x,y,size)
# 0.8 * (1 + 374k/100k) = 3.792 V nominal. Forced PWM avoids PFM overshoot.
passive('R60','374k 1%','MODEM_SUPPLY','MODEM_FB',94,48)
passive('R61','100k 1%','MODEM_FB','GND',97,49)
# Conservative battery UVLO: ~3.92 V rising / 3.43 V falling, tolerances documented.
passive('R62','390k 1%','VBAT','MODEM_REG_EN',90,42)
passive('R63','100k 1%','MODEM_REG_EN','GND',90,45)
# Pull EN low when the main switch is off, independently of firmware.
add('Q3','AO3400A','Transistor_FET:Q_NMOS_GSD','Package_TO_SOT_SMD:SOT-23',{1:'MODEM_DISABLE',2:'GND',3:'MODEM_REG_EN'},85,45)
add('Q4','AO3400A','Transistor_FET:Q_NMOS_GSD','Package_TO_SOT_SMD:SOT-23',{1:'SYS_EN',2:'GND',3:'MODEM_DISABLE'},80,45)
passive('R64','100k','VBAT','MODEM_DISABLE',85,41)
add_sheet('modem-power',entries,{'Handset:TPS63070RNM':s},14,(325,235))
board=parse((OUT/'handset.kicad_pcb').read_text())
for item in list(board):
    if not isinstance(item,list):continue
    if item[0]=='gr_text' and 'Modem regulated supply' in str(item[1]):board.remove(item)
    elif item[0]=='gr_line' and child(item,'layer')[1]=='User.1':
        if all(94.99<=float(pt[1])<=105.01 and 56.99<=float(pt[2])<=65.01 for pt in (child(item,'start'),child(item,'end'))):board.remove(item)
(OUT/'handset.kicad_pcb').write_text(dump(board)+'\n')
r=json.loads((OUT/'reservations.json').read_text())
(OUT/'reservations.json').write_text(json.dumps([x for x in r if x[0]!='Modem regulated supply'],indent=2)+'\n')
marker.write_text(json.dumps({'snapshot':str(snapshot.relative_to(ROOT)),'added':[c['ref'] for c in entries]},indent=2)+'\n')
print('Populated regulated modem supply; burst testing, UVLO review and adapter remain release blockers.')
