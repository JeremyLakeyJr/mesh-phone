#!/usr/bin/env python3
"""Check CC1101 RF copper continuity and return geometry, not RF performance."""
import json,math,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={'CC_RF_P':'U5.12 L5.1','CC_RF_N':'U5.13 L6.1','CC_BAL_P':'L5.2 C63.1 L7.1 C64.1','CC_BAL_N':'L6.2 C63.2 L8.1 C68.1','CC_SHUNT':'L7.2 C66.1','CC_MATCH':'C64.2 L8.2 L9.1','CC_LPF':'L9.2 L10.1 C65.1','CC_DC_BLOCK':'L10.2 C67.1','CC_RF_50R':'C67.2 J21.1','GND':'U1.1 C65.2 C66.2 C68.2 J21.2'}
def check_board(b):
 b.BuildConnectivity();pads={};checks=[];lengths={};gaps=[];samples=0
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.GetNumber():pads.setdefault(f.GetReference()+'.'+q.GetNumber(),[]).append(q)
 def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
 def ids(q):return {v.m_Uuid.AsString() for v in b.GetConnectivity().GetConnectedItems(q)}|{q.m_Uuid.AsString()}
 xy=lambda a:tuple(p.ToMM(v) for v in a)
 ground=ids(pads['U1.1'][0]);vias=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND' and t.m_Uuid.AsString() in ground]
 planes=[z.GetFilledPolysList(p.In2_Cu) for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname()=='GND' and z.IsOnLayer(p.In2_Cu)]
 for net,keys in GROUPS.items():
  qs=[q for k in keys.split() for q in pads[k]];group=ids(qs[0]);check(net+' full pad continuity',all(q.GetNetname()==net and q.m_Uuid.AsString() in group for q in qs))
  if net=='GND':continue
  ts=[t for t in b.GetTracks() if t.GetNetname()==net];check(net+' rear tracks without signal vias',bool(ts) and all(t.GetClass()=='PCB_TRACK' and t.GetLayer()==p.B_Cu for t in ts));check(net+' reviewed width',all(t.GetClass()=='PCB_TRACK' and t.GetWidth()==p.FromMM(.34 if net=='CC_RF_50R' else .2) for t in ts))
  lengths[net]=round(sum(p.ToMM(t.GetLength()) for t in ts if t.GetClass()=='PCB_TRACK'),4);check(net+' bounded length',0<lengths[net]<(3 if net in ('CC_RF_P','CC_RF_N') else 7))
  for t in ts:
   if t.GetClass()!='PCB_TRACK':continue
   a,z=xy(t.GetStart()),xy(t.GetEnd());d=math.dist(a,z)
   if not d:continue
   n=(-(z[1]-a[1])/d,(z[0]-a[0])/d);steps=math.ceil(d/.1)
   for i in range(steps+1):
    for offset in (0,-p.ToMM(t.GetWidth())/2-.1,p.ToMM(t.GetWidth())/2+.1):
     pt=(a[0]+(z[0]-a[0])*i/steps+n[0]*offset,a[1]+(z[1]-a[1])*i/steps+n[1]*offset);samples+=1
     if not any(poly.Contains(p.VECTOR2I(*(p.FromMM(v) for v in pt))) for poly in planes):gaps.append(dict(net=net,position_mm=pt))
 check('balanced IC fanout lengths',abs(lengths['CC_RF_P']-lengths['CC_RF_N'])<=.3)
 check('continuous adjacent ground under RF corridors',not gaps)
 for key in ['C65.2','C66.2','C68.2','J21.2']:
  for q in pads[key]:check(key+' local grounded return via',any(math.dist(xy(q.GetPosition()),xy(v.GetPosition()))<=1.6 for v in vias))
 return dict(passed=all(c['passed'] for c in checks),checks=checks,route_lengths_mm=lengths,reference_samples=samples,reference_gaps=gaps,qualification_open=['Qualify the custom CC1101 RF layout and 0.34mm antenna feed against the selected stackup, actual copper/ground clearance and TI reference layout; CAD dimensions do not certify 50 ohms or RF matching.','Measure conducted output, sensitivity, harmonics/spurs and antenna/case coexistence; tune matching and determine whether the optional 699MHz spur filter is required.'],fabrication_released=False)
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT;r=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')));(out/'cc1101-rf-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
