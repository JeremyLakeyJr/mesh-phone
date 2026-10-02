#!/usr/bin/env python3
"""Physical endpoint checks for supervisor distribution; not whole-board signoff."""
import json,math,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
groups={
'VSYS':'U3.1 C6.1 U26.1 U26.3 C77.1',
'PWR_AON_3V0':'U26.5 C78.1 U25.3 C79.1 C80.1 U27.8 C82.1 R76.1 R77.1 R78.1 TP2.1 U24.8 C60.1 R66.1 R69.1',
'GND':'U3.5 C6.2 C21.2 U26.2 U25.4 U27.4 C77.2 C78.2 C79.2 C80.2 C81.2 C82.2 C83.2 TP3.1',
'+3V3':'U7.6 C21.1 U27.1 U27.5 C81.1 R3.1 R4.1',
'CHG_I2C_SCL':'U25.28 R76.2 U24.6 U3.8',
'CHG_I2C_SDA':'U25.27 R77.2 U24.7 U3.7',
'PWR_HOST_SCL':'U25.18 U27.7',
'PWR_HOST_SDA':'U25.19 U27.6',
'I2C_SCL':'U1.17 U27.2 R3.2',
'I2C_SDA':'U1.18 U27.3 R4.2',
'PWR_NRST':'U25.5 R78.2 C83.1 TP6.1',
'PWR_SWDIO':'U25.20 TP4.1',
'PWR_SWCLK':'U25.21 TP5.1',
}
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));b.BuildConnectivity()
pads={f.GetReference()+'.'+q.GetNumber():q for f in b.GetFootprints() for q in f.Pads() if q.GetNumber()}
results=[]
for net,refs in groups.items():
    keys=refs.split();start=pads[keys[0]]
    assert all(pads[k].GetNetname()==net for k in keys),(net,keys)
    connected=list(b.GetConnectivity().GetConnectedItems(start))
    ids={item.m_Uuid.AsString() for item in connected}|{start.m_Uuid.AsString()}
    missing=[k for k in keys if pads[k].m_Uuid.AsString() not in ids]
    unexpected=sorted({item.GetNetname() for item in connected if item.GetNetname()!=net})
    results.append(dict(net=net,pads=keys,disconnected=missing,unexpected_nets=unexpected,passed=not(missing or unexpected)))
meta=json.loads((OUT/'supervisor-routing.json').read_text())
local_returns=[]
for key,pos in meta['ground_vias'].items():
    distance=math.dist(p.ToMM(pads[key].GetPosition()),pos)
    assert distance<=2.2,(key,distance)
    vias=[t for t in b.GetTracks() if isinstance(t,p.PCB_VIA) and t.GetNetname()=='GND' and math.dist(p.ToMM(t.GetPosition()),pos)<.001]
    assert len(vias)==1,(key,pos)
    connected=b.GetConnectivity().GetConnectedItems(pads[key])
    assert vias[0].m_Uuid.AsString() in {t.m_Uuid.AsString() for t in connected},key
    local_returns.append(dict(pad=key,via_distance_mm=round(distance,3)))
report=dict(passed=all(r['passed'] for r in results),groups=results,local_ground_returns=local_returns,
    checked_pads=sum(len(v.split()) for v in groups.values()),fabrication_released=False,
    scope='Supervisor power, ground, two I2C domains, charger expander and SWD; remaining host peripherals/distribution excluded')
(OUT/'supervisor-routing-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert report['passed'],'Supervisor endpoints disconnected'
