#!/usr/bin/env python3
"""Check the independent CE permission's topology, body-diode direction and copper."""
import copy,json,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
x=ET.parse(OUT/'netlist.xml').getroot()
nets={(n.get('ref'),n.get('pin')):net.get('name') for net in x.findall('./nets/net') for n in net.findall('node')}
contracts={('U25','6'):'CHG_ARM',('Q8','1'):'CHG_ARM',('Q8','2'):'GND',('Q8','3'):'CHG_CE_RETURN',('Q5','1'):'CHG_ENABLE',('Q5','2'):'CHG_CE_RETURN',('Q5','3'):'CHG_CE_N',('R79','1'):'CHG_ARM',('R79','2'):'GND',('R6','1'):'VSYS',('R6','2'):'CHG_CE_N',('U3','4'):'CHG_CE_N'}
def sink_path(n,enable,arm):
    # Logical switch topology only; not a transistor/transient simulation.
    edges={}
    for ref,on in [('Q5',enable),('Q8',arm)]:
        s,d=n[(ref,'2')],n[(ref,'3')]
        edges.setdefault(s,set()).add(d) # NMOS body diode: anode source, cathode drain.
        if on:edges.setdefault(d,set()).add(s)
    todo=['CHG_CE_N'];seen=set()
    while todo:
        net=todo.pop()
        if net=='GND':return True
        if net in seen:continue
        seen.add(net);todo.extend(edges.get(net,()))
    return False

def errors(n):
    err=[f'{r}.{pin} != {v}' for (r,pin),v in contracts.items() if n.get((r,pin))!=v]
    for net,expected in [('CHG_ARM',{('U25','6'),('Q8','1'),('R79','1')}),('CHG_CE_RETURN',{('Q5','2'),('Q8','3')})]:
        if {key for key,val in n.items() if val==net}!=expected:err.append(net+' has unexpected endpoint')
    for enable in [False,True]:
        for arm in [False,True]:
            if sink_path(n,enable,arm)!=(enable and arm):err.append('Invalid CE permission truth table')
    return err
assert not errors(nets),errors(nets)
mutations=[{('Q5','2'):'GND'},{('Q8','2'):'CHG_CE_RETURN',('Q8','3'):'GND'},{('R79','2'):'PWR_AON_3V0'},{('U25','6'):'CHG_ENABLE'},{('TP99','1'):'CHG_CE_RETURN'}]
for change in mutations:
    bad=copy.deepcopy(nets);bad.update(change);assert errors(bad),change
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));b.BuildConnectivity()
fps={f.GetReference():f for f in b.GetFootprints()}
pads={(r,pad.GetNumber()):pad for r,f in fps.items() for pad in f.Pads() if pad.GetNumber()}
for key,expected in contracts.items():assert pads[key].GetNetname()==expected,key
assert fps['Q8'].GetValue()=='AO3400A'
assert fps['R79'].GetValue()=='4.7k 1%'
groups=[('CHG_ARM',[('U25','6'),('R79','1'),('Q8','1')]),('CHG_CE_RETURN',[('Q5','2'),('Q8','3')]),('GND',[('R7','2'),('R79','2'),('Q8','2')]),('CHG_CE_N',[('Q5','3'),('R6','2'),('U3','4')])]
continuity=[]
for net,keys in groups:
    start=pads[keys[0]]
    connected=list(b.GetConnectivity().GetConnectedItems(start))
    ids={t.m_Uuid.AsString() for t in connected}|{start.m_Uuid.AsString()}
    missing=[r+'.'+pin for r,pin in keys if pads[(r,pin)].m_Uuid.AsString() not in ids]
    unexpected=sorted({t.GetNetname() for t in connected if t.GetNetname()!=net})
    assert not missing and not unexpected,(net,missing,unexpected)
    continuity.append(dict(net=net,pads=[r+'.'+pin for r,pin in keys],passed=True))
meta=json.loads((OUT/'charge-inhibit-update.json').read_text())
ids={t.m_Uuid.AsString() for t in b.GetTracks()}
assert not (ids & set(meta['removed_copper'])),'Old Q5 ground stub/via retained'
report=dict(passed=True,contract_pins=len(contracts),negative_tests=len(mutations),truth_table_cases=4,continuity=continuity,scope='Reset-default-off topology and routed CE permission; reset timing, leakage, IWDG and target firmware require qualification',fabrication_released=False)
(OUT/'charge-inhibit-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
