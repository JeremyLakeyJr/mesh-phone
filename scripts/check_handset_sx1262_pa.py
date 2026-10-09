#!/usr/bin/env python3
"""PA choke/bypass netlist and PCB contract, not RF layout qualification."""
import copy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
NETS={'SX_VR_PA':'U4.24 L13.1 C10.1 C101.1',
      'SX_RFO':'U4.23 L13.2 U36.1'}
PARTS={'L13':('47nH 2%','LQW15AN47NG80D','Inductor_SMD:L_0402_1005Metric'),
       'C10':('47nF 10% X7R 25V','GRM155R71E473KA88D','Capacitor_SMD:C_0402_1005Metric'),
       'C101':('47pF 5% C0G 50V','C1005C0G1H470J050BA','Capacitor_SMD:C_0402_1005Metric')}

def checks(nets,parts):
    failures=[]
    for net,names in NETS.items():
        if {pin for pin,value in nets.items() if value==net}!=set(names.split()):
            failures.append(net+' exact membership')
    for pin in ['C10.2','C101.2']:
        if nets.get(pin)!='GND':failures.append(pin+' ground')
    for ref,expected in PARTS.items():
        if parts.get(ref)!=expected:failures.append(ref+' value/MPN/footprint')
    return failures

def inspect(out):
    xml=ET.parse(out/'netlist.xml').getroot()
    nets={n.get('ref')+'.'+n.get('pin'):net.get('name') for net in xml.findall('./nets/net')
          for n in net.findall('node') if not n.get('ref').startswith('#')}
    parts={c.get('ref'):(c.findtext('value'),c.findtext('fields/field[@name="MPN"]'),c.findtext('footprint'))
           for c in xml.findall('./components/comp')}
    failures=checks(nets,parts);negative=[]
    for pin,value in [('L13.1','+3V3'),('L13.1','SX_VREG'),('L13.2','SX_DCC_SW'),
                      ('C10.1','SX_RFO'),('C101.1','SX_RFO'),('C101.2','SX_VR_PA'),
                      ('U36.1','SX_VR_PA')]:
        bad=copy.deepcopy(nets);bad[pin]=value
        negative.append(dict(mutation=pin+' -> '+value,rejected=bool(checks(bad,parts))))
    for ref,index,value in [('L13',0,'15uH 20%'),('C10',0,'100nF'),('C101',1,''),
                            ('L13',2,'Inductor_SMD:L_0201_0603Metric')]:
        bad=copy.deepcopy(parts);entry=list(bad[ref]);entry[index]=value;bad[ref]=tuple(entry)
        negative.append(dict(mutation=ref+' field '+str(index)+' -> '+value,rejected=bool(checks(nets,bad))))
    b=p.LoadBoard(str(out/'handset.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
    for ref,expected in PARTS.items():
        f=fps.get(ref)
        if f is None:
            failures.append(ref+' missing footprint');continue
        field=f.GetField('MPN')
        actual=(f.GetValue(),field.GetText() if field else '',str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName()))
        if actual!=expected:failures.append(ref+' PCB value/MPN/footprint')
        pads={q.GetNumber():q for q in f.Pads() if q.GetNumber()}
        if set(pads)!=set(['1','2']):failures.append(ref+' PCB pin count')
        for pin,q in pads.items():
            if q.GetNetname()!=nets.get(ref+'.'+pin):failures.append(ref+'.'+pin+' PCB net')
    return dict(passed=not failures and all(t['rejected'] for t in negative),failures=failures,
                negative_tests=negative,scope='PA circuit captured; no claim of PA copper continuity or RF qualification',
                qualification_open=[
                    ('Local PA copper is captured; qualify bypass/choke placement, RF parasitics and ground-return impedance.' if (out/'sx1262-local-rf-routing.json').exists() else 'PA placement is provisional and PA copper is incomplete; place VR_PA bypass/choke next to U4 RF pins with short ground returns.'),
                    '47nH/47nF/47pF values follow RAK4270, not a qualified BOM for this Johanson frontend; validate RF behavior and substitute-part parasitics.',
                    'Qualify PA current, supply droop, thermal rise, conducted power/harmonics and matching across the selected band.'],
                fabrication_released=False)

if __name__=='__main__':
    out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
    result=inspect(out);(out/'sx1262-pa-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));sys.exit(not result['passed'])
