#!/usr/bin/env python3
"""Verify local U10 boost/feedback/enable continuity and system ground."""
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
 'VSYS':'U10.3 C25.1 L2.1',
 'REG5_SW':'U10.5 L2.2',
 '+5V_RF':'U10.6 C26.1 R34.1',
 'REG5_FB':'U10.1 R34.2 R35.1',
 'SYS_EN':'U10.2 SW19.2 U7.1',
 'GND':'U7.8 U10.4 C25.2 C26.2 R35.2',
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

r=dict(passed=all(c['passed'] for c in checks),checked_physical_pads=count,groups=checks,
 fabrication_released=False,scope='Local U10 boost and enable; input/load distribution and electrical qualification remain')
(OUT/'reg5-continuity.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed'],'Power distribution remains disconnected'
