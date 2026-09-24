#!/usr/bin/env python3
"""Independent native-netlist contract for SX1262 core DC-DC support.

Semtech DS rev1.2 Fig14-2 and Table5-3. Does not qualify copper or RF.
"""
import copy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def checks(nets,values,mpns):
    result=[]
    def check(name,valid):result.append(dict(check=name,passed=bool(valid)))
    pins={('U4','1'):'+3V3',('U4','7'):'SX_VREG',('U4','9'):'SX_DCC_SW',
          ('U4','10'):'+3V3',('U4','11'):'+3V3',('U4','24'):'SX_VR_PA',
          ('L12','1'):'SX_DCC_SW',('L12','2'):'SX_VREG',('C9','1'):'SX_VREG',('C9','2'):'GND'}
    pins.update({('U4',p):'GND' for p in ('2','5','8','20','25')})
    for key,net in pins.items():check('.'.join(key)+' contract',nets.get(key)==net)
    for ref in ('C8','C75','C76'):
        check(ref+' supply bypass',nets.get((ref,'1'))=='+3V3' and nets.get((ref,'2'))=='GND')
        check(ref+' specified value',values.get(ref)=='100nF 10% X7R 16V')
        check(ref+' specified MPN',mpns.get(ref)=='GRM155R71C104KA88D')
    check('C9 regulator capacitance',values.get('C9')=='470nF 10% X5R 10V')
    check('C9 specified MPN',mpns.get('C9')=='GRM155R61A474KE15D')
    check('L12 regulator inductance',values.get('L12')=='15uH 20%')
    check('L12 recommended MPN',mpns.get('L12')=='MLZ2012M150WT000')
    for net,members in {'SX_DCC_SW':{('U4','9'),('L12','1')},
                        'SX_VREG':{('U4','7'),('L12','2'),('C9','1')}}.items():
        check(net+' exact membership',{key for key,n in nets.items() if n==net}==members)
    return result


def inspect(path):
    xml=ET.parse(path/'netlist.xml').getroot()
    nets={(n.get('ref'),n.get('pin')):net.get('name') for net in xml.findall('./nets/net') for n in net.findall('node')}
    comps={c.get('ref'):c for c in xml.findall('./components/comp')}
    values={r:c.findtext('value') for r,c in comps.items()}
    mpns={r:c.findtext('fields/field[@name="MPN"]') for r,c in comps.items()}
    results=checks(nets,values,mpns);negative=[]
    for key,new in [(('L12','2'),'+3V3'),(('C9','2'),'SX_DCC_SW'),(('U4','1'),'SX_VREG')]:
        bad=copy.deepcopy(nets);bad[key]=new
        negative.append(dict(mutation='.'.join(key)+' -> '+new,rejected=not all(x['passed'] for x in checks(bad,values,mpns))))
    bad=copy.deepcopy(values);bad['C9']='100nF'
    negative.append(dict(mutation='C9 old incorrect 100nF',rejected=not all(x['passed'] for x in checks(nets,bad,mpns))))
    return dict(scope='SX1262 core DC-DC schematic contract, not copper continuity or complete radio qualification',
        passed=all(x['passed'] for x in results) and all(x['rejected'] for x in negative),
        checks=len(results),failures=[x for x in results if not x['passed']],negative_tests=negative,fabrication_released=False)


if __name__=='__main__':
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'hardware/handset-rev-a/generated'
    result=inspect(path);(path/'sx1262-power-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));sys.exit(0 if result['passed'] else 1)
