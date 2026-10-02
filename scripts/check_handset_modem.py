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
 'VBAT':'U20.12 U20.13 C50.1 C51.1 R62.1 R64.1',
 'MODEM_L1':'U20.11 L4.1',
 'MODEM_L2':'U20.9 L4.2',
 'MODEM_SUPPLY':'U20.7 U20.8 C52.1 C53.1 C54.1 R60.1',
 'MODEM_FB':'U20.5 R60.2 R61.1',
 'MODEM_VAUX':'U20.3 C55.1',
 'MODEM_REG_EN':'U20.14 R62.2 R63.1 Q3.3',
 'SYS_EN':'Q4.1 SW19.2 U7.1',
 'MODEM_DISABLE':'R64.2 Q3.1 Q4.3',
 'GND':'U7.8 U20.1 U20.4 U20.10 U20.15 C50.2 C51.2 C52.2 C53.2 C54.2 C55.2 R61.2 R63.2 Q3.2 Q4.2',
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
 fabrication_released=False,scope='Local U20 stage/enable network only; external battery/modem feeds and qualification remain')
(OUT/'modem-continuity.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed'],'Power distribution remains disconnected'
