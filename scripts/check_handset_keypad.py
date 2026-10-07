#!/usr/bin/env python3
"""Check all 64 physical switch contacts and eight U2 matrix pins."""
import json,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={}
for row in range(4):GROUPS['KEY_ROW'+str(row)]=['U2.'+str(8-row)]+['SW'+str(4*row+col+1)+'.1' for col in range(4)]
for col in range(4):GROUPS['KEY_COL'+str(col)]=['U2.'+str(9+col)]+['SW'+str(4*row+col+1)+'.2' for row in range(4)]
def check_board(b):
 b.BuildConnectivity();pads={}
 for f in b.GetFootprints():
  for q in f.Pads():pads.setdefault(f.GetReference()+'.'+q.GetNumber(),[]).append(q)
 checks=[]
 for net,names in GROUPS.items():
  entries=[(name,q) for name in names for q in pads[name]];seed=entries[0][1]
  ids={q.m_Uuid.AsString() for q in b.GetConnectivity().GetConnectedItems(seed)}|{seed.m_Uuid.AsString()}
  missing=[name+':'+q.m_Uuid.AsString() for name,q in entries if q.m_Uuid.AsString() not in ids]
  wrong=[name for name,q in entries if q.GetNetname()!=net]
  checks.append(dict(net=net,physical_pads=len(entries),missing=missing,wrong_net=wrong,passed=not(missing or wrong) and len(entries)==9))
 return dict(passed=all(c['passed'] for c in checks),groups=checks,fabrication_released=False)
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
 report=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')))
 (out/'keypad-routing-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));sys.exit(not report['passed'])
