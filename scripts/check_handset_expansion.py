#!/usr/bin/env python3
"""Check expansion circuit and native copper independently of routing manifests."""
import json,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from handset_expansion_contract import PINS,validate
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={
 '+3V3':'U7.6 U14.1 C40.1 R42.1 U33.10 U34.20 U35.14 C91.1 C92.1 C93.1 R86.1 R1.1 R3.1 R4.1',
 'EXP_3V3':'U14.6 C41.1 R87.1 J16.2',
 'EXP_PWR_EN':'U33.1 U35.1 R83.1 U14.3',
 'EXP_IO_ARM':'U33.3 U35.2 R84.1',
 'EXP_FAULT_N':'U14.4 R42.2 U33.2 U35.13',
 'EXP_IO_OE_N':'U35.12 U34.19 R86.2',
 'EXP_ILIM':'U14.5 R41.1','EXP_GPIO_SPARE':'U33.4 R85.1',
 'MCU_EN':'U1.3 U33.6 R1.2 C1.1',
 'I2C_SCL':'U1.17 U33.8 U34.2 R3.2','I2C_SDA':'U1.18 U33.9 U34.3 R4.2',
 'SPI_SCK':'U1.20 U34.4','SPI_MOSI':'U1.21 U34.5','SPI_MISO':'U1.22 U34.6',
 'EXP_CS':'U1.7 U34.7','EXP_IRQ':'U1.8 U34.8',
 'GND':'U7.8 U14.2 R41.2 C40.2 C41.2 U33.5 U34.9 U34.10 U34.11 U35.3 U35.4 U35.5 U35.7 U35.9 U35.10 U35.11 C91.2 C92.2 C93.2 R83.2 R84.2 R85.2 R87.2 J16.1 J16.10 U15.3 U15.8 U16.3 U16.8 C1.2',
}
for ref,channel,pin in [('R20','SCL',18),('R21','SDA',17),('R22','SCK',16),('R23','MOSI',15),('R24','MISO',14),('R25','CS',13),('R26','IRQ',12)]:GROUPS['EXP_SW_'+channel]=f'U34.{pin} {ref}.1'
for net,ref,jpin,esd in [('EXP_SCL','R20',3,'U15.1'),('EXP_SDA','R21',4,'U15.2'),('EXP_SCK','R22',5,'U15.4'),('EXP_MOSI','R23',6,'U15.5'),('EXP_MISO','R24',7,'U16.1'),('EXP_CS_PORT','R25',8,'U16.2'),('EXP_IRQ_PORT','R26',9,'U16.4')]:GROUPS[net]=f'{ref}.2 J16.{jpin} {esd}'

def check_board(board):
 board.BuildConnectivity();pads={f.GetReference()+'.'+q.GetNumber():q for f in board.GetFootprints() for q in f.Pads() if q.GetNumber()}
 contract=[]
 for ref,pins in PINS.items():
  for pin,net in pins.items():
   q=pads.get(ref+'.'+pin)
   if not q or (q.GetNetname()!=net if net is not None else not q.GetNetname().startswith('unconnected-(')):contract.append(ref+'.'+pin)
 checks=[]
 for net,names in GROUPS.items():
  names=names.split();seed=pads.get(names[0]);connected=list(board.GetConnectivity().GetConnectedItems(seed)) if seed else []
  ids={q.m_Uuid.AsString() for q in connected}|({seed.m_Uuid.AsString()} if seed else set())
  missing=[n for n in names if n not in pads or pads[n].m_Uuid.AsString() not in ids]
  wrong=[n for n in names if n not in pads or pads[n].GetNetname()!=net]
  unexpected=sorted({q.GetNetname() for q in connected if q.GetNetname()!=net})
  checks.append(dict(net=net,pads=names,disconnected=missing,wrong_net=wrong,unexpected_nets=unexpected,passed=not(missing or wrong or unexpected)))
 return dict(passed=not contract and all(g['passed'] for g in checks),groups=checks,pin_contract_failures=contract,fabrication_released=False,scope='Connectivity and topology only; not startup, isolation leakage, current, thermal, fault recovery or signal-timing qualification')

def check_circuit(out):
 spec={c['ref']:c for c in json.loads((out/'connectivity.json').read_text())};xml=ET.parse(out/'netlist.xml').getroot()
 values={c.attrib['ref']:c.findtext('value') for c in xml.findall('./components/comp')}
 nets={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')}
 fields={c.attrib['ref']:{f.attrib['name']:f.text for f in c.findall('./fields/field')} for c in xml.findall('./components/comp')}
 validate(spec,values,nets,fields)
 return spec,values,nets,fields
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT;check_circuit(out)
 report=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')))
 (out/'expansion-routing-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));sys.exit(0 if report['passed'] else 1)
