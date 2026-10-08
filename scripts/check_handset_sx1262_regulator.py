#!/usr/bin/env python3
"""Check local regulator continuity, switch-node topology and open-pad controls."""
import json,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={'SX_DCC_SW':'U4.9 L12.1','SX_VREG':'U4.7 L12.2 C9.1','GND':'U1.1 C9.2 U4.8 U4.25'}
def check_board(b):
 b.BuildConnectivity();pads={f.GetReference()+'.'+q.GetNumber():q for f in b.GetFootprints() for q in f.Pads() if q.GetNumber()}
 errors=[]
 for net,names in GROUPS.items():
  entries=[pads[n] for n in names.split()];seed=entries[0]
  connected=list(b.GetConnectivity().GetConnectedItems(seed));ids={q.m_Uuid.AsString() for q in connected}|{seed.m_Uuid.AsString()}
  if not all(q.GetNetname()==net and q.m_Uuid.AsString() in ids for q in entries) or any(q.GetNetname()!=net for q in connected):errors.append(net+' continuity')
 for net,limit in [('SX_DCC_SW',4),('SX_VREG',8)]:
  tracks=[t for t in b.GetTracks() if t.GetNetname()==net]
  if not tracks or any(t.GetClass()!='PCB_TRACK' or t.GetLayer()!=p.B_Cu for t in tracks):errors.append(net+' must stay on B.Cu without vias')
  if sum(p.ToMM(t.GetLength()) for t in tracks)>limit:errors.append(net+' excessive length')
 return dict(passed=not errors,failures=errors,fabrication_released=False)
def inspect(out):
 result=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')));negative=[]
 for name in ['L12.1','L12.2','C9.1','C9.2','U4.8','U4.25']:
  b=p.LoadBoard(str(out/'handset.kicad_pcb'));ref,pin=name.split('.')
  f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
  q=next(q for q in f.Pads() if q.GetNumber()==pin);q.SetPosition(p.VECTOR2I(p.FromMM(200),p.FromMM(200)))
  negative.append(dict(open_pad=name,rejected=not check_board(b)['passed']))
 result['negative_tests']=negative;result['passed'] &= all(t['rejected'] for t in negative)
 return result
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
 result=inspect(out);(out/'sx1262-regulator-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.exit(not result['passed'])
