#!/usr/bin/env python3
"""Cross-check saved KiCad netlist against real board pads and case coordinates.

This verifies a WIP artifact's integrity, never electrical completeness.
Run native netlist export/ERC/DRC first; the JSON report keeps their failures.
"""
from collections import Counter
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import pcbnew as pcb

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'hardware/handset-rev-a/generated'
pcb.SwigPyIterator.next=pcb.SwigPyIterator.__next__
board=pcb.LoadBoard(str(OUT/'handset.kicad_pcb'))
spec=json.loads((OUT/'connectivity.json').read_text())
xml=ET.parse(OUT/'netlist.xml').getroot()
sch={}
for net in xml.findall('./nets/net'):
    for node in net.findall('node'):
        sch[(node.get('ref'),node.get('pin'))]=net.get('name')
fps={fp.GetReference():fp for fp in board.GetFootprints()}
checks=[]
def check(label, condition):
    checks.append({'check':label,'passed':bool(condition)})
for c in spec:
    ref=c['ref'];fp=fps[ref]
    pads={}
    for p in fp.Pads():
        if p.GetNumber(): pads.setdefault(p.GetNumber(),[]).append(p.GetNetname())
    for pin,net in c['nets'].items():
        if net is None: continue
        check(f'{ref}.{pin}: schematic = {net}',sch.get((ref,pin))==net)
        check(f'{ref}.{pin}: board = {net}',pin in pads and all(n==net for n in pads[pin]))
    check(ref+': schematic footprint',xml.find(f'./components/comp[@ref="{ref}"]/footprint').text==c['footprint'])
check('retained N16R8',fps['U1'].GetValue()=='ESP32-S3-WROOM-1-N16R8')
for pin in ['28','29','30']:
    check('PSRAM pad '+pin+' unused',all(p.GetNetname().startswith('unconnected-(') for p in fps['U1'].Pads() if p.GetNumber()==pin))
for row,y in enumerate([111,126,141,156]):
    for col,x in enumerate([77.5,92.5,107.5,122.5]):
        p=fps['SW'+str(row*4+col+1)].GetPosition()
        check(f'key {row},{col} aligns with enclosure',abs(pcb.ToMM(p.x)-x)<.001 and abs(pcb.ToMM(p.y)-y)<.001)
for i,(x,y) in enumerate([(69.5,32),(130.5,32),(69.5,168),(130.5,168)],1):
    p=fps['H'+str(i)].GetPosition()
    check('mount H'+str(i),abs(pcb.ToMM(p.x)-x)<.001 and abs(pcb.ToMM(p.y)-y)<.001)
    check('mount drill stays inside PCB H'+str(i),min(x-67,133-x,y-29,171-y)>1.1)
check('modem supply isolated from charger SYS',sch[('J9','1')]=='MODEM_SUPPLY' and sch[('U3','1')]=='VSYS')
contracts={
 ('U3','10'):'USB_VBUS', ('U3','2'):'VBAT', ('U3','6'):'BAT_TS',
 ('SW19','2'):'SYS_EN', ('SW19','3'):'GND',
 ('U1','20'):'SPI_SCK', ('U1','21'):'SPI_MOSI', ('U1','22'):'SPI_MISO',
 ('U1','23'):'SX_CS', ('U1','15'):'IR_RX', ('U2','14'):'LCD_BL_EN',
 ('U8','7'):'I2C_SCL', ('U8','8'):'I2C_SDA',
 ('U12','2'):'GPS_HOST_RX', ('U12','3'):'GPS_HOST_TX',
 ('U12','7'):'+3V3', ('U12','8'):'+3V3',
 ('U14','1'):'+3V3', ('U14','2'):'GND', ('U14','5'):'EXP_ILIM', ('U14','6'):'EXP_3V3',
 ('U20','12'):'VBAT', ('U20','13'):'VBAT', ('U20','7'):'MODEM_SUPPLY', ('U20','8'):'MODEM_SUPPLY',
 ('Q1','1'):'IR_GATE', ('Q1','2'):'GND', ('Q1','3'):'IR_LED_K',
 ('J26','6'):'GND', ('J26','7'):'+3V3', ('J26','8'):'+3V3', ('J26','9'):'+3V3',
 ('J26','34'):'SPI_MOSI', ('J26','36'):'LCD_DC', ('J26','37'):'SPI_SCK', ('J26','38'):'LCD_CS',
}
if (OUT/'power-entry-update.json').exists():
    contracts.update({
        ('U3','10'):'USB_PROTECTED', ('U3','4'):'CHG_CE_N',
        ('U3','7'):'I2C_SDA', ('U3','8'):'I2C_SCL',
        ('J1','1'):'BAT_PACK_POS', ('F2','1'):'BAT_PACK_POS', ('F2','2'):'VBAT',
        ('F1','1'):'USB_VBUS', ('F1','2'):'USB_FUSED',
        ('U21','6'):'USB_FUSED', ('U21','1'):'USB_PROTECTED', ('U21','4'):'USB_PWR_EN',
        ('U22','1'):'USB_CC1', ('U22','2'):'USB_CC2', ('U22','3'):'GND',
        ('U22','7'):'USB_CC_HIGH_N', ('U22','11'):'GND', ('U22','12'):'USB_AON_3V3',
        ('U23','2'):'USB_FUSED', ('U23','3'):'USB_AON_3V3',
        ('U24','1'):'CHG_ENABLE', ('U24','2'):'USB_LEGACY_EN',
        ('U24','3'):'USB_CC_QUALIFIED_N', ('U24','5'):'USB_PWR_FAULT_N',
        ('Q5','1'):'CHG_ENABLE', ('Q5','2'):'GND', ('Q5','3'):'CHG_CE_N',
        ('Q6','1'):'USB_CC_HIGH_N', ('Q6','2'):'USB_AON_3V3', ('Q6','3'):'USB_CC_AUTO',
        ('Q7','1'):'USB_CC_AUTO', ('Q7','2'):'GND', ('Q7','3'):'USB_CC_QUALIFIED_N',
        ('D1','1'):'USB_FUSED', ('D1','2'):'GND',
        ('D2','1'):'USB_CC_AUTO', ('D2','2'):'USB_LEGACY_EN', ('D2','3'):'USB_PWR_EN',
        ('R6','1'):'VSYS', ('R6','2'):'CHG_CE_N',
        ('R7','1'):'CHG_ENABLE', ('R7','2'):'GND',
        ('R68','1'):'USB_LEGACY_EN', ('R68','2'):'GND',
    })
    check('programmable charger populated',fps['U3'].GetValue()=='BQ25186DLHR')
    for net in ('USB_CC1','USB_CC2'):
        check(net+': no duplicate external Rd',not any(
            fp.GetReference().startswith('R') and any(p.GetNetname()==net for p in fp.Pads())
            for fp in fps.values()))
for key,net in contracts.items():
    check(f'review contract {key[0]}.{key[1]} = {net}',sch.get(key)==net)
for pin in ('6','9','15','18'):
    check('GNSS unused pin '+pin,all(p.GetNetname().startswith('unconnected-(') for p in fps['U12'].Pads() if p.GetNumber()==pin))
for net in xml.findall('./nets/net'):
    name=net.get('name')
    if name.startswith('unconnected-('):
        nodes=net.findall('node')
        pads=[pad for fp in fps.values() for pad in fp.Pads() if pad.GetNetname()==name]
        check(name+': electrically isolated',len(nodes)==1 and len(pads)==1 and
              not any(t.GetNetname()==name for t in board.GetTracks()))
for ref,number in [('U13',33),('U20',15)]:
    check(ref+' numbered land count',len({p.GetNumber() for p in fps[ref].Pads() if p.GetNumber()})==number)
for ref in ('L1','L2','L3','L4'):
    check(ref+' current-rated package',str(fps[ref].GetFPID().GetLibItemName())=='Coilcraft_XFL4020')
check('4 copper layers',board.GetCopperLayerCount()==4)
erc=json.loads((OUT/'erc.json').read_text())
drc=json.loads((OUT/'drc.json').read_text())
erc_items=[v for s in erc['sheets'] for v in s['violations']]
report={'status':'INCOMPLETE — NOT FOR FABRICATION OR POWER',
 'integrity_checks':len(checks),'integrity_passed':sum(c['passed'] for c in checks),
 'integrity_failures':[c for c in checks if not c['passed']],
 'components':len(spec),'copper_layers':4,
 'erc_by_type':dict(Counter(v['type'] for v in erc_items)),
 'drc_by_type':dict(Counter(v['type'] for v in drc['violations'])),
 'unconnected_items':len(drc['unconnected_items']),
 'schematic_parity_findings':len(drc.get('schematic_parity',[])),
 'placement_errors':[v for v in drc['violations'] if v['type'] in
     ('courtyards_overlap','malformed_courtyard','shorting_items','clearance','solder_mask_bridge','copper_edge_clearance')],
 'fabrication_released':False,
 'unresolved_placement_zones':len(json.loads((OUT/'reservations.json').read_text()))}
(OUT/'verification-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert not report['integrity_failures'], 'Schematic/PCB integrity mismatch'
assert not report['placement_errors'], 'Physical overlap/clearance errors remain; inspect native DRC'
assert not report['schematic_parity_findings'], 'Native schematic/PCB parity mismatch'
