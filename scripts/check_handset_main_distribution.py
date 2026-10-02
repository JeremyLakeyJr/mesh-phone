#!/usr/bin/env python3
"""Verify physical U7/ESP32/SW19 distribution, including every ESP32 ground pad."""
import json,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));b.BuildConnectivity()
pads={}
for f in b.GetFootprints():
 for q in f.Pads():
  if q.GetNumber():pads.setdefault(f.GetReference()+'.'+q.GetNumber(),[]).append(q)
groups={
 'VSYS':'U3.1 C6.1 C20.1 U7.10 SW19.1',
 'SYS_EN':'SW19.2 R30.1 U7.1',
 '+3V3':'U7.6 C21.1 C22.1 C2.1 C3.1 U1.2',
 'GND':'U3.5 C6.2 U7.8 C20.2 C21.2 SW19.3 U1.1 U1.40 U1.41 C1.2 C2.2 C3.2',
}
checks=[];count=0
for net,names in groups.items():
 entries=[(name,q) for name in names.split() for q in pads[name]];count+=len(entries)
 seed=entries[0][1];connected=list(b.GetConnectivity().GetConnectedItems(seed))
 ids={q.m_Uuid.AsString() for q in connected}|{seed.m_Uuid.AsString()}
 wrong=[name for name,q in entries if q.GetNetname()!=net]
 missing=[name for name,q in entries if q.m_Uuid.AsString() not in ids]
 unexpected=sorted({q.GetNetname() for q in connected if q.GetNetname()!=net})
 checks.append(dict(net=net,pads=names.split(),physical_pad_count=len(entries),disconnected=missing,wrong_net=wrong,unexpected_nets=unexpected,passed=not(missing or wrong or unexpected)))
assert len(pads['U1.41'])==13,'Audit changed module ground footprint'
r=dict(passed=all(c['passed'] for c in checks),checked_physical_pads=count,groups=checks,
 fabrication_released=False,scope='Main U7 input, switch control and ESP32 power/ground/bypass only; other loads, logic wiring and current/thermal qualification excluded')
(OUT/'main-distribution-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed'],'Power distribution remains disconnected'
