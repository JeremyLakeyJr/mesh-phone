"""Independent net-contract and placement checks; never an electrical release approval."""
from pathlib import Path
import hashlib
import json
from collections import Counter
import xml.etree.ElementTree as ET
from cad_sexpr import parse,children,child,prop

base=Path(__file__).resolve().parent
d=base/'revF-gps-expansion'
root=ET.parse(d/'netlist.xml').getroot()
nets={(p.get('ref'),p.get('pin')):n.get('name') for n in root.findall('nets/net') for p in n.findall('node')}
checks=[]
def check(name,condition):
    checks.append({'check':name,'passed':bool(condition)})
def contract(ref,mapping):
    for pin,net in mapping.items():check(f'{ref}.{pin} = {net}',nets.get((ref,str(pin)))==net)
contract('U1',{3:'/MCU_EN',4:'/GPS_HOST_TX',5:'/GPS_HOST_RX',6:'/GPS_PPS',7:'/EXP_CS',8:'/EXP_IRQ',9:'/LCD_RESET',10:'/TP_RESET',12:'/TOUCH_INT',20:'/SPI_SCK',21:'/SPI_MOSI',22:'/SPI_MISO',23:'/SX1262_CS',24:'/CC1101_CS',25:'/CC1101_GDO0',27:'/MCU_BOOT'})
for p in [16,26,28,29,30]:check(f'U1.{p} deliberately NC',nets['U1',str(p)].startswith('unconnected-'))
contract('U2',{1:'/GND',2:'/GND',3:'/GND',4:'/KEY_R1',5:'/KEY_R2',6:'/KEY_R3',7:'/KEY_R4',8:'/GND',9:'/KEY_C1',10:'/KEY_C2',11:'/KEY_C3',12:'/KEY_C4',14:'/I2C_SCL',15:'/I2C_SDA',16:'/3V3'})
prefix='/GPS and rear expansion/'
contract('U9',{1:'/GND',2:prefix+'GPS_TX',3:prefix+'GPS_RX',4:'/GPS_PPS',7:'/3V3',8:'/3V3',10:'/GND',11:prefix+'GPS_ANT',12:'/GND'})
for p in [6,15,18]:check(f'U9.{p} deliberately NC',nets['U9',str(p)].startswith('unconnected-'))
contract('R6',{1:'/GPS_HOST_TX',2:prefix+'GPS_RX'})
contract('R7',{1:prefix+'GPS_TX',2:'/GPS_HOST_RX'})
contract('U10',{1:'/3V3',2:'/GND',3:'/3V3',5:prefix+'EXP_ILIM',6:prefix+'EXP_3V3'})
contract('J16',{1:'/GND',2:prefix+'EXP_3V3',3:prefix+'EXP_SCL',4:prefix+'EXP_SDA',5:prefix+'EXP_SCK',6:prefix+'EXP_MOSI',7:prefix+'EXP_MISO',8:prefix+'EXP_CS_PORT',9:prefix+'EXP_IRQ_PORT',10:'/GND'})
contract('SW1',{1:'/BAT_CHARGE',2:'/VBAT'})
contract('J13',{1:'/BAT_CHARGE',2:'/GND'})
def footprints(path):
    return {prop(f,'Reference')[2]:f for f in children(parse(path.read_text()),'footprint')}
original=footprints(base/'owasso1.kicad_pcb')
revision=footprints(d/'owasso1.kicad_pcb')
for ref,f in original.items():
    g=revision.get(ref)
    check(f'{ref} original position/orientation/side preserved',g is not None and child(f,'at')==child(g,'at') and child(f,'layer')==child(g,'layer'))
for ref in ['U9','U10','J15','J16']:check(f'{ref} rear-side placement',child(revision[ref],'layer')[1]=='B.Cu')
for ref,f in revision.items():
    for p in children(f,'pad'):
        if not p[1] or ref.startswith('H'):continue
        net=child(p,'net')
        check(f'PCB {ref}.{p[1]} matches exported schematic',(net[-1] if net else None)==nets.get((ref,p[1])))
drc=json.loads((d/'drc-final.json').read_text())
erc=json.loads((d/'erc.json').read_text())
ev=[v for s in erc['sheets'] for v in s['violations']]
summary={
 'release_status':'ENGINEERING ONLY — DO NOT FABRICATE OR POWER',
 'checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),
 'checks_failed':[c for c in checks if not c['passed']],
 'drc':{'violations_by_type':dict(Counter(v['type'] for v in drc['violations'])),'severities':dict(Counter(v['severity'] for v in drc['violations'])),'unconnected_items':len(drc['unconnected_items']),'schematic_parity':len(drc['schematic_parity'])},
 'erc':{'violations_by_type':dict(Counter(v['type'] for v in ev)),'severities':dict(Counter(v['severity'] for v in ev))},
 'known_release_blockers':['Battery protection and charger/power-path redesign','Undefined 3.3V supply and invalid 5V boost layout','US modem/carrier/VoLTE selection and validated carrier pinout','Remaining IR, RFID, fuel gauge, SIM and radio control interfaces','RF/USB impedance, ESD, enclosure clearance and hardware/firmware validation'],
 'sha256':{f:hashlib.sha256((d/f).read_bytes()).hexdigest() for f in ['owasso1.kicad_pcb','owasso1.kicad_sch','gps-expansion.kicad_sch','owasso1.kicad_pro','netlist.xml']},
 'checks':checks,
}
(d/'verification-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['checks','sha256']},indent=2))
assert all(c['passed'] for c in checks),'Connection/placement regression — inspect summary'
