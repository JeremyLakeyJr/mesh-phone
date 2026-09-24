#!/usr/bin/env python3
"""Rebuild the schematic presentation in a staged project, retaining part identity.

Never runs against the saved project. Circuit changes are explicit in the input
manifest; native netlist comparison is required before installation.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import uuid
from collections import defaultdict
from cad_sexpr import Q, parse, dump, child, children, prop

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'hardware/handset-rev-a/generated'
OUT = Path('/tmp/handset-schematic-rebuild')
UID = lambda name: str(uuid.uuid5(uuid.NAMESPACE_URL, 'handset-schematic-rebuild/'+name))

PAGES = [
 ('core','ESP32 host, boot and reset','U1 R1 R2 C1 C2 C3 SW17 SW18',
  'Retain N16R8. Module pads 28/29/30 belong to octal PSRAM. USB programming uses the USB sheet.'),
 ('keys','Key matrix and trackball','U2 C4 R3 R4 R5 J7 '+' '.join('SW'+str(i) for i in range(1,17)),
  'TCA8418: 4 rows x 4 columns; remaining pins are firmware-configured GPIO. Confirm PIM447 harness orientation.'),
 ('usb','USB-C data and ESD','USB1 U17',
  'CC1/CC2 terminate at the sink controller on usb-detect. Data pair goes to the ESP32. Shield/ground return needs layout review.'),
 ('usb-input','Fused USB input and eFuse','F1 D1 U21 R65 R66 R67 C59',
  'TPS25200 R_ILIM = 100k, 1%. F1/TVS pulse coordination requires bench validation. No USB PD negotiation.'),
 ('usb-detect','USB-C source detection and permission','U22 U23 Q6 Q7 D2 R8 R9 R69 R70 C56 C57 C58',
  'Sink-only internal Rd. OUT1 low authorizes Type-C 1.5A/3A. Legacy permission requires USB enumeration; see charger-policy.json.'),
 ('power','Battery, thermistor and programmable charger','U3 J1 J2 F2 Q5 R6 R7 C5 C6 C7',
  'Verify actual battery polarity. J2 is a battery-mounted 10k B3435 NTC. CE defaults OFF. Firmware must apply charger-policy.json.'),
 ('power-control','Power control and fuel gauge','U24 U8 C60 C23 R68',
  'I2C: TCA9536 0x41, MAX17048 0x36, charger 0x6A. Preload low output latches before enabling charger-control outputs.'),
 ('reg3','Main 3.3 V buck-boost supply','U7 SW19 L1 C20 C21 C22 R30 R31 R32 R33',
  'TPS63802 local PCB copper is routed. External distribution, effective capacitance, thermal limits and load transients remain to qualify.'),
 ('aux-power','Auxiliary 5 V and 1.8 V supplies','U10 U11 L2 L3 R34 R35 C25 C26 C27 C28',
  'Switching loops must be short in PCB layout. The 5 V rail also supplies display backlight and the LF reader.'),
 ('modem-power','Regulated modem supply and enable','U20 L4 Q3 Q4 C50 C51 C52 C53 C54 C55 R60 R61 R62 R63 R64',
  'Nominal output 3.792 V. Exact modem burst current and MakerFocus pack current budget are unresolved release blockers.'),
 ('radios','SX1262 LoRa radio','U4 J20 C8 C9 C10 R10',
  '902-928 MHz design intent. Clock, DC-DC and RF matching must follow the selected Semtech reference circuit.'),
 ('cc-radio','CC1101 sub-GHz radio','U5 J21 R11 R12 C11 C12',
  '868/915 MHz matching design intent. A bare differential RF port cannot connect directly to the 50-ohm antenna.'),
 ('lf-radio','125 kHz reader analog circuit','U9 J10 C24',
  'HTRC110 requires its oscillator, QGND/CEXT bypass, resonant coil network and a timing-capable host interface.'),
 ('lf-support','LF reader logic translation','U18 U19 C45 C46 R50 R51',
  'AHCT inputs accept 3.3 V logic at 5 V supply; LVC return buffer is powered at 3.3 V. Host timing remains a design requirement.'),
 ('gnss-antennas','GNSS receiver and passive antenna','U12 J22 C29 C30',
  'MAX-M10S passive antenna. V_BCKP remains open: cold starts after power removal. No direct LiPo connection.'),
 ('nfc','NFC reader, oscillator and local supplies','U13 Y1 R40 C31 C32 C33 C34 C35 C36 C37 C38 C39',
  'ST25R3916B needs a tuned case-mounted loop and TX/RX matching network. Verify crystal load against the selected crystal.'),
 ('audio','Media speaker amplifier and digital microphone','U6 MK1 J3 C13 C14 C15 R13',
  'Top-mounted media speaker uses differential outputs: neither speaker wire is ground. Digital microphone is case-bottom mounted.'),
 ('interfaces','Cellular adapter and call-audio harnesses','J4 J5 J6 J8 J9',
  'Replaceable modem adapter owns SIM, cellular RF and modem-level translation. No universal-carrier guarantee. Speaker top / mic bottom.'),
 ('protection','Protected external module port','J16 U14 U15 U16 R20 R21 R22 R23 R24 R25 R26 R41 R42 C40 C41',
  'J16 pin order retained. Switch accessories with power off. TPS2553 limit and ESD path require qualification.'),
 ('storage-ir','MicroSD and case-mounted infrared','J23 Q1 J24 J25 R43 R44 R45 R46 R47 R48 R49 C42 C43 C44',
  'SPI microSD, transistor-driven IR LED, filtered receiver supply. Confirm case LED/receiver polarity and GPIO3 boot behavior.'),
 ('display','External display, touch and backlight','J26 Q2 R52 R53 R54 R55 R56 R57 R58 R59 C47 C48 C49',
  'ER-TFT024IPS-3 connector contract. Verify purchased CTP option, FPC orientation, LED branches and supply tolerances.'),
]


class Sheet:
    def __init__(self,name,title,number,note,rootid,spec,instances,symbols):
        self.name=name;self.id=UID(name);self.rootid=rootid;self.spec=spec
        self.instances=instances;self.symbols=symbols;self.pins={};self.used=set();self.wired=set();self.serial=0
        self.tree=parse(f'''(kicad_sch (version 20250114) (generator "eeschema")
          (uuid "{self.id}") (paper "A3") (title_block (title "{title}")
          (date "2026-09-24") (rev "A - engineering draft")
          (comment 1 "Circuit review in progress - not released for fabrication")) (lib_symbols))''')
        self.text(title,15,15,2)
        import textwrap
        self.text('\n'.join(textwrap.wrap(note,125)),15,22,1.15)
        self.text('Engineering draft / named nets are common / NC = intentional unused pin',15,282,1)
        self.number=number

    def ident(self):
        self.serial+=1;return UID(self.name+'/'+str(self.serial))

    def text(self,value,x,y,size=1.27):
        self.tree.append(['text',Q(value),['at',str(x),str(y),'0'],
                          ['effects',['font',['size',str(size),str(size)]],['justify','left','top']],['uuid',Q(self.ident())]])

    def wire(self,a,b):
        if math.dist(a,b)<1e-6:return
        self.tree.append(parse(f'(wire (pts (xy {a[0]:.4f} {a[1]:.4f}) (xy {b[0]:.4f} {b[1]:.4f})) (stroke (width 0) (type default)) (uuid "{self.ident()}"))'))

    def dot(self,pos):
        self.tree.append(parse(f'(junction (at {pos[0]} {pos[1]}) (diameter 0) (color 0 0 0 0) (uuid "{self.ident()}"))'))

    def label(self,net,pos,angle=0,justify='left'):
        if net=='GND':
            self.ground(pos)
            return
        self.tree.append(['global_label',Q(net),['shape','bidirectional'],['at',str(pos[0]),str(pos[1]),str(angle)],
                          ['effects',['font',['size','1','1']],['justify',justify]],['uuid',Q(self.ident())]])

    def ground(self,pos):
        libid='power:GND'
        if libid not in self.used:
            sym=copy.deepcopy(self.symbols[libid]);child(self.tree,'lib_symbols').append(sym);self.used.add(libid)
        ref='#PWR'+str(self.number*1000+self.serial)
        x,y=pos
        self.tree.append(parse(f'''(symbol (lib_id "power:GND") (at {x} {y} 0) (unit 1)
          (in_bom yes) (on_board yes) (dnp no) (uuid "{self.ident()}")
          (property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
          (property "Value" "GND" (at {x} {y+5.08} 0) (effects (font (size 1 1))))
          (pin "1" (uuid "{self.ident()}"))
          (instances (project "handset" (path "/{self.rootid}/{self.id}" (reference "{ref}") (unit 1)))))'''))

    def flag(self,key):
        """External source after a passive fuse; never used to conceal a missing supply."""
        pos,_,net=self.pins[key];libid='power:PWR_FLAG'
        if libid not in self.used:
            child(self.tree,'lib_symbols').append(copy.deepcopy(self.symbols[libid]));self.used.add(libid)
        ref='#FLG'+str(self.number*1000+self.serial);x,y=pos
        self.tree.append(parse(f'''(symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1)
          (in_bom yes) (on_board yes) (dnp no) (uuid "{self.ident()}")
          (property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
          (property "Value" "PWR_FLAG" (at {x} {y-5.08} 0) (effects (font (size 1 1)) (hide yes)))
          (pin "1" (uuid "{self.ident()}"))
          (instances (project "handset" (path "/{self.rootid}/{self.id}" (reference "{ref}") (unit 1)))))'''))

    def place(self,ref,x,y,angle=0):
        c=self.spec[ref];inst=copy.deepcopy(self.instances[ref]);libid=c['libid'];sym=copy.deepcopy(self.symbols[libid])
        if libid not in self.used:
            child(self.tree,'lib_symbols').append(sym);self.used.add(libid)
        child(inst,'at')[1:]=[str(x),str(y),str(angle)]
        prop(inst,'Value')[2]=Q(c['value']);prop(inst,'Footprint')[2]=Q(c['footprint'])
        for name,yy in [('Reference',y-18),('Value',y-15.5)]:
            pr=prop(inst,name);child(pr,'at')[1:]=[str(x),str(yy),str(angle % 180)]
            effects=child(pr,'effects');effects[:]=parse('(effects (font (size 1.1 1.1)))')
        for pr in children(inst,'property'):
            if pr[1] not in ('Reference','Value'):
                child(pr,'at')[1:]=[str(x),str(y),'0']
        for project in children(child(inst,'instances'),'project'):
            for path in children(project,'path'):path[1]=Q('/'+self.rootid+'/'+self.id)
        self.tree.append(inst);c['sheet']=self.name
        pp=[]
        for unit in children(sym,'symbol'):
            for pin in children(unit,'pin'):
                num=str(child(pin,'number')[1]);px,py,pa=map(float,child(pin,'at')[1:])
                a=math.radians(angle);pos=(round(x+px*math.cos(a)-py*math.sin(a),4),round(y-px*math.sin(a)-py*math.cos(a),4))
                self.pins[ref+'.'+num]=(pos,(pa+angle)%360,c['nets'].get(num));pp.append(pos)
        if pp:
            top=min(p[1] for p in pp)
            for name,dy in [('Reference',-10.16),('Value',-7.62)]:child(prop(inst,name),'at')[2]=str(round(top+dy,4))
        return inst

    def bank(self,refs,x,y):
        net1=self.spec[refs[0]]['nets']['1'];net2=self.spec[refs[0]]['nets']['2']
        for i,ref in enumerate(refs):
            xx=x+i*25.4
            sym=self.symbols[self.spec[ref]['libid']]
            pin=next(p for u in children(sym,'symbol') for p in children(u,'pin') if str(child(p,'number')[1])=='1')
            px,py=map(float,child(pin,'at')[1:3]);angle=round(math.degrees(math.atan2(px,py)))%360
            inst=self.place(ref,xx,y,angle)
            for name,dy in [('Reference',-1.27),('Value',1.27)]:
                pr=prop(inst,name);child(pr,'at')[1:]=[str(xx+3.81),str(y+dy),'0'];child(pr,'effects')[:]=parse('(effects (font (size 0.95 0.95)) (justify left))')
            a=self.pins[ref+'.1'][0];b=self.pins[ref+'.2'][0]
            # Both terminals have explicit shared rails, not a label on every part.
            self.wire(a,(a[0],y-10.16));self.wire(b,(b[0],y+10.16))
            if i:
                self.wire((x+(i-1)*25.4,y-10.16),(xx,y-10.16));self.wire((x+(i-1)*25.4,y+10.16),(xx,y+10.16))
            self.wired.update([ref+'.1',ref+'.2'])
        self.label(net1,(x,y-10.16),0);self.label(net2,(x,y+10.16),0)

    def matrix(self):
        for row in range(4):
            yy=157.48+row*25.4;bus_y=yy+7.62
            self.wire((35.56,bus_y),(213.36,bus_y));self.label('KEY_ROW'+str(row),(35.56,bus_y),0)
            for col in range(4):
                xx=66.04+col*50.8;ref='SW'+str(row*4+col+1);self.place(ref,xx,yy)
                a=self.pins[ref+'.1'][0];z=self.pins[ref+'.2'][0];colx=xx+15.24
                self.wire(a,(a[0],bus_y));self.dot((a[0],bus_y))
                self.wire(z,(colx,z[1]));self.dot((colx,z[1]));self.wired.update([ref+'.1',ref+'.2'])
                if row==0:self.wire((colx,142.24),(colx,233.68));self.label('KEY_COL'+str(col),(colx,142.24),90)

    def path(self,net,*nodes,label=False):
        points=[]
        for node in nodes:
            if isinstance(node,str):
                pos,_,actual=self.pins[node]
                assert actual==net,(node,actual,net)
                self.wired.add(node);points.append(pos)
            else:points.append(node)
        for a,b in zip(points,points[1:]):
            assert abs(a[0]-b[0])<.001 or abs(a[1]-b[1])<.001,('diagonal schematic wire',net,a,b)
            self.wire(a,b)
        if label:self.label(net,points[-1] if net=='GND' or (isinstance(nodes[0],str) and not isinstance(nodes[-1],str)) else points[0])

    def passive(self,ref,x,y,angle=0):
        inst=self.place(ref,x,y,angle)
        for name,dy in [('Reference',-1.27),('Value',1.27)]:
            pr=prop(inst,name);child(pr,'at')[1:]=[str(x+3.81),str(y+dy),str(angle % 180)]
            child(pr,'effects')[:]=parse('(effects (font (size 1 1)) (justify left))')
        if angle % 180:
            for name,dy in [('Reference',-10.16),('Value',-7.62)]:
                pr=prop(inst,name);child(pr,'at')[1:]=[str(x),str(y+dy),'90']
                child(pr,'effects')[:]=parse('(effects (font (size 1 1)))')

    def charger(self):
        self.place('U3',170.18,96.52)
        for ref,x,y,a in [('C5',124.46,101.6,0),('C6',238.76,101.6,0),('C7',238.76,162.56,0),
                          ('F2',284.48,147.32,270),('R6',109.22,68.58,0),('R7',71.12,114.3,0)]:
            self.passive(ref,x,y,a)
        self.place('J1',350.52,147.32);self.place('J2',78.74,177.8);self.place('Q5',109.22,109.22)
        self.path('USB_PROTECTED',(101.6,86.36),(124.46,86.36),'U3.10',label=True)
        self.path('USB_PROTECTED','C5.1',(124.46,86.36));self.dot((124.46,86.36))
        self.path('VSYS',(269.24,86.36),(238.76,86.36),'U3.1',label=True)
        self.path('VSYS','C6.1',(238.76,86.36));self.dot((238.76,86.36))
        self.path('VBAT','U3.2',(210.82,96.52),(210.82,147.32),(238.76,147.32),'F2.2',label=True)
        self.path('VBAT','C7.1',(238.76,147.32));self.dot((238.76,147.32))
        self.path('BAT_PACK_POS','F2.1','J1.1',label=True)
        self.path('GND','J1.2',(337.82,149.86),(337.82,177.8),label=True)
        self.path('VSYS','R6.1',(109.22,55.88),label=True)
        self.path('CHG_CE_N','R6.2',(109.22,96.52),'U3.4',label=True)
        self.path('CHG_CE_N','Q5.3',(111.76,96.52));self.dot((111.76,96.52))
        self.path('CHG_ENABLE',(45.72,109.22),(71.12,109.22),'Q5.1',label=True)
        self.path('CHG_ENABLE','R7.1',(71.12,109.22));self.dot((71.12,109.22))
        for key in ['C5.2','C6.2','C7.2','Q5.2','R7.2','U3.5','U3.11']:
            pos=self.pins[key][0];self.path('GND',key,(pos[0],pos[1]+7.62),label=True)
        self.text('Protected 103665 pack / 3000 mAh\nF2 does not enforce the pack operating-current limit.',279.4,187.96,1.15)
        self.text('Battery-mounted thermistor\nDo not substitute a fixed resistor.',48.26,198.12,1.15)
        self.text('Charge enable: default OFF\nProgram and verify limits before driving CHG_ENABLE high.',45.72,134.62,1.15)

    def core(self):
        inst=self.place('U1',170.18,111.76)
        for name,yy in [('Reference',76.2),('Value',78.74)]:child(prop(inst,name),'at')[1:]=['203.2',str(yy),'0']
        self.passive('R1',101.6,71.12);self.passive('C1',101.6,111.76)
        self.place('SW18',127,111.76,270)
        self.passive('R2',139.7,144.78);self.place('SW17',172.72,167.64)
        self.passive('C2',264.16,76.2);self.passive('C3',299.72,76.2)
        self.path('MCU_EN','U1.3',(101.6,88.9),'R1.2',label=True)
        self.path('MCU_EN','C1.1',(101.6,88.9));self.dot((101.6,88.9))
        self.path('MCU_EN','SW18.1',(127,88.9),(101.6,88.9));self.dot((127,88.9))
        self.path('MCU_BOOT','U1.27',(133.35,93.98),(133.35,167.64),(139.7,167.64),'SW17.1',label=True)
        self.path('MCU_BOOT','R2.2',(139.7,167.64));self.dot((139.7,167.64))
        self.path('+3V3','U1.2',(170.18,55.88),(299.72,55.88),label=True)
        for ref in ('C2','C3'):
            pos=self.pins[ref+'.1'][0];self.path('+3V3',ref+'.1',(pos[0],55.88));self.dot((pos[0],55.88))
        for ref in ('R1','R2'):
            pos=self.pins[ref+'.1'][0];self.path('+3V3',ref+'.1',(pos[0],pos[1]-7.62),label=True)
        for key in ('C1.2','C2.2','C3.2','SW17.2','SW18.2','U1.1','U1.40','U1.41'):
            if key in ('U1.40','U1.41'):self.wired.add(key);continue
            pos=self.pins[key][0];self.path('GND',key,(pos[0],pos[1]+7.62),label=True)
        self.text('RESET / EN: 10k pull-up + 1uF\nBOOT held low during reset selects download mode.',45.72,200.66,1.15)
        self.text('USB D+/D- go to USB-C / ESD sheet.\nGPIO35/36/37 are reserved for internal octal PSRAM.\nKeep strapping GPIO45/46 unassigned until boot-state review.',238.76,167.64,1.15)

    def reg3(self):
        self.place('U7',170.18,96.52);self.place('SW19',63.5,86.36)
        self.passive('L1',170.18,45.72,90)
        for ref,x,y in [('C20',124.46,101.6),('C21',269.24,101.6),('C22',304.8,101.6),
                        ('R31',228.6,93.98),('R32',228.6,124.46),('R30',101.6,114.3),('R33',345.44,101.6)]:
            self.passive(ref,x,y)
        self.path('REG3_L1','U7.9',(165.1,45.72),'L1.1',label=True)
        self.path('REG3_L2','U7.7',(175.26,45.72),'L1.2',label=True)
        self.path('VSYS',(101.6,86.36),(124.46,86.36),'U7.10',label=True)
        self.path('VSYS','C20.1',(124.46,86.36));self.dot((124.46,86.36))
        self.path('+3V3','U7.6',(345.44,86.36),label=True)
        for key in ['R31.1','C21.1','C22.1','R33.1']:
            pos=self.pins[key][0];self.path('+3V3',key,(pos[0],86.36));self.dot((pos[0],86.36))
        self.path('REG3_FB','U7.4',(208.28,96.52),(208.28,109.22),(228.6,109.22),'R31.2',label=True)
        self.path('REG3_FB','R32.1',(228.6,109.22));self.dot((228.6,109.22))
        self.path('SYS_EN',(86.36,96.52),(101.6,96.52),'U7.1',label=True)
        self.path('SYS_EN','R30.1',(101.6,96.52));self.dot((101.6,96.52))
        for key in ('C20.2','C21.2','C22.2','R30.2','R32.2','U7.2','U7.3','U7.8'):
            pos,angle,_=self.pins[key]
            end=(pos[0]-7.62,pos[1]) if angle==0 else (pos[0],pos[1]+7.62)
            self.path('GND',key,end,label=True)
        self.path('REG3_PG','R33.2',(345.44,116.84),label=True)
        self.text('0.6 V reference x (1 + 560k / 100k) = 3.3 V nominal.\nFeedback senses the output capacitor node; keep it clear of the switching loop.',208.28,157.48,1.15)
        self.text('SW19 controls SYS_EN.\nBattery / charger circuitry can remain energized while logic rails are off.',45.72,190.5,1.15)

    def finish(self):
        emitted=set()
        # Dense connector ground pins share a drawn return bus instead of
        # overlapping ground symbols on every 2.54 mm row.
        for ref in ('J26',):
            pins=[(key,pos) for key,(pos,angle,net) in self.pins.items()
                  if key.startswith(ref+'.') and net=='GND' and angle==0]
            if pins:
                bx=pins[0][1][0]-3.81
                ys=sorted({pos[1] for _,pos in pins})
                for key,pos in pins:
                    self.wire(pos,(bx,pos[1]));self.dot((bx,pos[1]));self.wired.add(key)
                self.wire((bx,ys[0]),(bx,ys[-1]+7.62));self.ground((bx,ys[-1]+7.62))
        for key,(pos,angle,net) in self.pins.items():
            if key in self.wired:continue
            if (pos,net) in emitted:continue
            emitted.add((pos,net))
            if net is None:
                self.tree.append(parse(f'(no_connect (at {pos[0]} {pos[1]}) (uuid "{self.ident()}"))'));continue
            a=math.radians(angle);end=(round(pos[0]-7.62*math.cos(a),4),round(pos[1]+7.62*math.sin(a),4))
            self.wire(pos,end);self.label(net,end,angle,'right' if angle in (0,90) else 'left')
        (OUT/(self.name+'.kicad_sch')).write_text(dump(self.tree)+'\n')


def main():
    assert not (SOURCE/'schematic-rebuild.json').exists(), 'Installed revision exists; preserve later manual edits.'
    OUT.mkdir(exist_ok=True)
    for path in SOURCE.iterdir():
        if path.is_file():shutil.copy2(path,OUT/path.name)
    shutil.copytree(SOURCE/'Handset.pretty',OUT/'Handset.pretty',dirs_exist_ok=True)
    spec={c['ref']:c for c in json.loads((SOURCE/'connectivity.json').read_text())}
    instances={};symbols={}
    for path in SOURCE.glob('*.kicad_sch'):
        tree=parse(path.read_text())
        for symbol in children(child(tree,'lib_symbols'),'symbol'):symbols[str(symbol[1])]=symbol
        for inst in children(tree,'symbol'):instances[str(prop(inst,'Reference')[2])]=inst
    for library,part in [('power','GND'),('power','PWR_FLAG'),('Device','D_Zener')]:
        sym=copy.deepcopy(next(s for s in children(parse(Path('/usr/share/kicad/symbols',library+'.kicad_sym').read_text()),'symbol') if s[1]==part))
        sym[1]=Q(library+':'+part);symbols[library+':'+part]=sym
    # The populated SMF5.0A is unidirectional: show its cathode, not a bidirectional TVS.
    spec['D1']['libid']='Device:D_Zener';child(instances['D1'],'lib_id')[1]=Q('Device:D_Zener')
    # Explicit circuit corrections derived from manufacturer reference drawings.
    spec['U4']['nets']['1']='+3V3'  # SX1262 PA supply VDD_IN, not the regulated core rail.
    spec['U9']['nets']['5']='GND'   # HTRC110 MODE is grounded for short local host wiring.
    for libid,number,typ in [('Audio:MAX98357A','17','power_in'),('Handset:TPS63070RNM','8','passive'),
                             ('Handset:MAX17048','6','input')]:
        symbol=symbols[libid]
        if not libid.startswith('Handset:'):
            old=libid;libid='Handset:MAX98357A_Audited';symbol=copy.deepcopy(symbol);symbol[1]=Q(libid)
            for unit in children(symbol,'symbol'):unit[1]=Q(str(unit[1]).replace('MAX98357A','MAX98357A_Audited'))
            symbols[libid]=symbol
            for ref,c in spec.items():
                if c['libid']==old:c['libid']=libid;child(instances[ref],'lib_id')[1]=Q(libid)
        for unit in children(symbol,'symbol'):
            for pin in children(unit,'pin'):
                if str(child(pin,'number')[1])==number:pin[1]=typ
    # Logical pin arrangement; manufacturer pin numbers/functions stay unchanged.
    symbol=symbols['Handset:BQ25186']
    locations={10:(-20.32,10.16,0),4:(-20.32,0,0),6:(-20.32,-10.16,0),
               1:(20.32,10.16,180),2:(20.32,0,180),7:(20.32,-10.16,180),
               8:(20.32,-15.24,180),3:(20.32,15.24,180),9:(20.32,-20.32,180),
               5:(-5.08,-30.48,90),11:(5.08,-30.48,90)}
    for unit in children(symbol,'symbol'):
        for rect in children(unit,'rectangle'):
            child(rect,'start')[1:]=['-15.24','20.32'];child(rect,'end')[1:]=['15.24','-25.4']
        for pin in children(unit,'pin'):
            child(pin,'at')[1:]=list(map(str,locations[int(child(pin,'number')[1])]))
            child(pin,'length')[1]='5.08'
    symbol=symbols['Handset:TPS63802']
    locations={10:(-20.32,10.16,0),1:(-20.32,0,0),2:(-20.32,-10.16,0),
               6:(20.32,10.16,180),4:(20.32,0,180),5:(20.32,-20.32,180),
               9:(-5.08,25.4,270),7:(5.08,25.4,270),
               3:(-5.08,-25.4,90),8:(5.08,-25.4,90)}
    for unit in children(symbol,'symbol'):
        for rect in children(unit,'rectangle'):
            child(rect,'start')[1:]=['-15.24','20.32'];child(rect,'end')[1:]=['15.24','-20.32']
        for pin in children(unit,'pin'):
            child(pin,'at')[1:]=list(map(str,locations[int(child(pin,'number')[1])]))
            child(pin,'length')[1]='5.08'
    rootid=str(child(parse((SOURCE/'handset.kicad_sch').read_text()),'uuid')[1])
    root=parse(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{rootid}") (paper "A2") (lib_symbols))')
    allrefs=[];manifest=[]
    for index,(name,title,reftext,note) in enumerate(PAGES,2):
        refs=reftext.split();allrefs.extend(refs)
        page=Sheet(name,title,index,note,rootid,spec,instances,symbols)
        pairs=defaultdict(list);large=[]
        for ref in refs:
            if name=='keys' and ref.startswith('SW'):continue
            c=spec[ref]
            if set(c['nets'])=={'1','2'} and all(c['nets'].values()) and not ref.startswith(('J','SW')):
                pairs[tuple(c['nets'][n] for n in ('1','2'))].append(ref)
            else:large.append(ref)
        custom=name in ('power','core','reg3')
        for i,ref in enumerate([] if custom else large):
            if name=='display':
                page.place(ref,86.36 if ref=='J26' else 330.2,121.92 if ref=='J26' else 60.96)
                continue
            if len(large)>3:page.place(ref,53.34+i*(101.6 if len(large)==4 else 76.2),86.36)
            else:page.place(ref,86.36+i*132.08,86.36)
        start=157.48
        banks=[rs[j:j+3] for rs in pairs.values() for j in range(0,len(rs),3)]
        for i,rs in enumerate([] if custom else banks):
            if name=='display':x,y=180.34+(i%2)*101.6,101.6+(i//2)*33.02
            elif name=='keys':x,y=330.2,119.38+i*33.02
            else:x,y=40.64+(i%3)*124.46,start+(i//3)*33.02
            assert y+10.16<269, (name,'passive banks exceed page',rs)
            page.bank(rs,x,y)
        if name=='keys':page.matrix()
        if name=='power':page.charger()
        if name=='core':page.core()
        if name=='reg3':page.reg3()
        if name=='power':
            page.flag('F2.2');page.flag('J1.2')
            page.text('Supply flags identify the external protected pack through F2 and its return.',238.76,220.98,1)
        if name=='usb-input':
            page.flag('F1.2')
            page.text('Supply flag: external USB VBUS through F1. No internal source is implied.',15.24,250.19,1)
        page.finish();manifest.append({'name':name,'title':title,'page':index,'refs':refs})
        col=(index-2)%3;row=(index-2)//3;x=25.4+col*187.96;y=45.72+row*45.72
        root.append(parse(f'''(sheet (at {x} {y}) (size 160.02 25.4) (stroke (width 0.254) (type solid))
          (fill (color 0 0 0 0)) (uuid "{page.id}")
          (property "Sheetname" "{title}" (at {x} {y-2.54} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
          (property "Sheetfile" "{name}.kicad_sch" (at {x} {y+27.94} 0) (effects (font (size 1 1)) (justify left top)))
          (instances (project "handset" (path "/{rootid}" (page "{index}")))))'''))
    assert len(allrefs)==len(set(allrefs))==len(spec), 'Each component must occur exactly once'
    assert set(allrefs)==set(spec)
    root.append(['text',Q('HANDSET REV A / SYSTEM SCHEMATIC INDEX'),['at','25.4','15.24','0'],['effects',['font',['size','3','3']],['justify','left']],['uuid',Q(UID('root-title'))]])
    root.append(['text',Q('Engineering draft. Retained ESP32-S3 / MakerFocus 3000 mAh / external display / all peripheral interfaces.'),['at','25.4','25.4','0'],['effects',['font',['size','1.27','1.27']],['justify','left']],['uuid',Q(UID('root-note'))]])
    (OUT/'handset.kicad_sch').write_text(dump(root)+'\n')
    library=parse((SOURCE/'Handset.kicad_sym').read_text())
    for libid,symbol in symbols.items():
        if not libid.startswith('Handset:'):continue
        name=libid.split(':',1)[1]
        for old in list(children(library,'symbol')):
            if old[1]==name:library.remove(old)
        replacement=copy.deepcopy(symbol);replacement[1]=Q(name);library.append(replacement)
    (OUT/'Handset.kicad_sym').write_text(dump(library)+'\n')
    (OUT/'connectivity.json').write_text(json.dumps(list(spec.values()),indent=2)+'\n')
    (OUT/'schematic-rebuild.json').write_text(json.dumps({
        'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.is_file() and p.suffix in ('.kicad_sch','.kicad_pcb','.kicad_pro','.kicad_sym')},
        'pages':manifest,'components':len(spec),'fabrication_released':False,
        'scope':'All-sheet rebuild; native netlist/electrical and visual review required before install'},indent=2)+'\n')
    print('Rebuilt',len(PAGES)+1,'sheets in',OUT)


if __name__=='__main__':main()
