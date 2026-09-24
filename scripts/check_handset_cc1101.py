#!/usr/bin/env python3
"""Check the CC1101 manufacturer-derived circuit, not RF performance.

The expected graph is independent of the generator and rejects missing,
shorted or swapped matching branches. Uses the native exported KiCad netlist.
"""
from collections import Counter
import copy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

# TI SWRS061I Fig11 / SWRR045 rev3.0, with optional C126/L125 omitted.
# Each unordered pair is the two terminals of one passive component.
RF={
 'L5':('CC_RF_P','CC_BAL_P','12nH 5%'),       # L121
 'L6':('CC_RF_N','CC_BAL_N','12nH 5%'),       # L131
 'L7':('CC_BAL_P','CC_SHUNT','18nH 5%'),      # L122
 'L8':('CC_BAL_N','CC_MATCH','18nH 5%'),      # L132
 'L9':('CC_MATCH','CC_LPF','12nH 5%'),        # L123
 'L10':('CC_LPF','CC_DC_BLOCK','12nH 5%'),    # L124
 'C63':('CC_BAL_P','CC_BAL_N','1pF 0.25pF C0G 50V'),
 'C64':('CC_BAL_P','CC_MATCH','1.5pF 0.25pF C0G 50V'),
 'C65':('CC_LPF','GND','3.3pF 0.25pF C0G 50V'),
 'C66':('CC_SHUNT','GND','100pF 5% C0G 50V'),
 'C67':('CC_DC_BLOCK','CC_RF_50R','12pF 5% C0G 50V'),
 'C68':('CC_BAL_N','GND','1.5pF 0.25pF C0G 50V'),
}


def checks(nets, values, mpns):
    result=[]
    def check(name,valid):result.append(dict(check=name,passed=bool(valid)))
    for ref,(a,b,value) in RF.items():
        check(ref+' TI matching branch',Counter(nets.get((ref,p)) for p in ('1','2'))==Counter((a,b)))
        check(ref+' TI matching value',values.get(ref)==value)
    for pin,net in {'1':'SPI_SCK','2':'SPI_MISO','3':'CC_GDO2','4':'CC_VDD',
      '5':'CC_DCOUPL','6':'CC_GDO0','7':'CC_CS','8':'CC_X1','9':'CC_VDD',
      '10':'CC_X2','11':'CC_VDD','12':'CC_RF_P','13':'CC_RF_N','14':'CC_VDD',
      '15':'CC_VDD','16':'GND','17':'CC_RBIAS','18':'CC_VDD','19':'GND',
      '20':'SPI_MOSI','21':'GND'}.items():check('U5.'+pin+' contract',nets.get(('U5',pin))==net)
    for key,net in {('Y2','1'):'CC_X1',('Y2','2'):'GND',('Y2','3'):'CC_X2',('Y2','4'):'GND',
                   ('C61','1'):'CC_X1',('C61','2'):'GND',('C62','1'):'CC_X2',('C62','2'):'GND',
                   ('C11','1'):'CC_DCOUPL',('C11','2'):'GND',('L11','1'):'+3V3',('L11','2'):'CC_VDD',
                   ('R11','1'):'CC_RBIAS',('R11','2'):'GND',('R12','1'):'+3V3',('R12','2'):'CC_CS',
                   ('J21','1'):'CC_RF_50R',('J21','2'):'GND',('TP1','1'):'CC_GDO2'}.items():
        check('.'.join(key)+' contract',nets.get(key)==net)
    for ref in ['C12','C69','C70','C71','C72','C73','C74']:
        check(ref+' bypass rail',nets.get((ref,'1'))=='CC_VDD' and nets.get((ref,'2'))=='GND')
        check(ref+' bypass value',values.get(ref)==('1uF 10% X5R 10V' if ref=='C74' else '100nF 10% X7R 16V'))
    for ref in ('C61','C62'):check(ref+' CL10 load',values.get(ref)=='15pF 5% C0G 50V')
    check('26MHz specified crystal',mpns.get('Y2')=='ABM8-26.000MHZ-10-D-1-G-T')
    check('bias resistor',values.get('R11')=='56k 1%')
    check('crystal load estimate',15/2+2.5==10)
    check('first-year crystal error budget',10+15+2<40)
    # Exact node membership catches unintended bypasses or extra grounded legs.
    expected={}
    for ref,(a,b,_) in RF.items():
        expected.setdefault(a,set()).add(ref);expected.setdefault(b,set()).add(ref)
    for net in ('CC_BAL_P','CC_BAL_N','CC_SHUNT','CC_MATCH','CC_LPF','CC_DC_BLOCK'):
        check(net+' branch membership',{ref for (ref,pin),n in nets.items() if n==net}==expected[net])
    return result


def inspect(path):
    xml=ET.parse(path/'netlist.xml').getroot()
    nets={(n.get('ref'),n.get('pin')):net.get('name') for net in xml.findall('./nets/net') for n in net.findall('node')}
    comps={c.get('ref'):c for c in xml.findall('./components/comp')}
    values={ref:c.findtext('value') for ref,c in comps.items()}
    mpns={ref:c.findtext('fields/field[@name="MPN"]') for ref,c in comps.items()}
    results=checks(nets,values,mpns)
    negative=[]
    for key,new in [(('C63','2'),'GND'),(('L8','2'),'CC_BAL_P'),(('Y2','2'),'CC_X1'),(('C11','1'),'CC_VDD')]:
        changed=copy.deepcopy(nets);changed[key]=new
        negative.append(dict(mutation='.'.join(key)+' -> '+new,rejected=not all(x['passed'] for x in checks(changed,values,mpns))))
    wrong=copy.deepcopy(values);wrong['C61']='27pF'
    negative.append(dict(mutation='C61 wrong crystal load',rejected=not all(x['passed'] for x in checks(nets,wrong,mpns))))
    return dict(scope='CC1101 schematic topology and component specification; not copper continuity or RF qualification',
        passed=all(x['passed'] for x in results) and all(x['rejected'] for x in negative),
        checks=len(results),failures=[x for x in results if not x['passed']],negative_tests=negative,
        fabrication_released=False)


if __name__=='__main__':
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'hardware/handset-rev-a/generated'
    result=inspect(path);(path/'cc1101-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));sys.exit(0 if result['passed'] else 1)
