#!/usr/bin/env python3
"""Inspect CC1101 support copper and masked thermal vias; not RF qualification."""
import json, math, sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
BRANCHES={'C12':'4','C69':'9','C70':'11','C71':'14','C72':'15','C73':'18'}
GROUPS={'CC_X1':'U5.8 Y2.1 C61.1','CC_X2':'U5.10 Y2.3 C62.1','CC_DCOUPL':'U5.5 C11.1','CC_RBIAS':'U5.17 R11.1','CC_VDD':'L11.2 C74.1 '+' '.join('U5.'+pin+' '+ref+'.1' for ref,pin in BRANCHES.items()),'+3V3':'U4.10 L11.1','GND':'U1.1 U5.16 U5.19 U5.21 Y2.2 Y2.4 '+' '.join(r+'.2' for r in ['C11','C12','C61','C62','C69','C70','C71','C72','C73','C74','R11'])}
xy=lambda a:(p.ToMM(a.x),p.ToMM(a.y))

def check_board(b):
 b.BuildConnectivity();conn=b.GetConnectivity();fps={f.GetReference():f for f in b.GetFootprints()};pads={f.GetReference()+'.'+q.GetNumber():q for f in b.GetFootprints() for q in f.Pads() if q.GetNumber()}
 checks=[];lengths={};gaps=[];samples=0
 def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
 def ids(q):return {v.m_Uuid.AsString() for v in conn.GetConnectedItems(q)}|{q.m_Uuid.AsString()}
 for net,keys in GROUPS.items():
  qs=[pads[k] for k in keys.split()];group=ids(qs[0]);check(net+' full pad continuity',all(q.GetNetname()==net and q.m_Uuid.AsString() in group for q in qs))
 tracks=list(b.GetTracks());ground_ids=ids(pads['U1.1']);ground_vias=[v for v in tracks if v.GetClass()=='PCB_VIA' and v.GetNetname()=='GND' and v.m_Uuid.AsString() in ground_ids]
 planes=[z.GetFilledPolysList(p.In2_Cu) for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname()=='GND' and z.IsOnLayer(p.In2_Cu)]
 for net,bound in [('CC_X1',10),('CC_X2',8),('CC_DCOUPL',2),('CC_RBIAS',2)]:
  ts=[t for t in tracks if t.GetNetname()==net];check(net+' rear copper without vias',bool(ts) and all(t.GetClass()=='PCB_TRACK' and t.GetLayer()==p.B_Cu for t in ts))
  lengths[net]=round(sum(p.ToMM(t.GetLength()) for t in ts if t.GetClass()=='PCB_TRACK'),4);check(net+' bounded length',0<lengths[net]<bound)
  for t in ts:
   if t.GetClass()!='PCB_TRACK' or net not in ('CC_X1','CC_X2'):continue
   a,z=xy(t.GetStart()),xy(t.GetEnd());d=math.dist(a,z)
   if not d:continue
   n=(-(z[1]-a[1])/d,(z[0]-a[0])/d);steps=math.ceil(d/.1)
   for i in range(steps+1):
    for offset in (0,-p.ToMM(t.GetWidth())/2-.1,p.ToMM(t.GetWidth())/2+.1):
     pt=(a[0]+(z[0]-a[0])*i/steps+n[0]*offset,a[1]+(z[1]-a[1])*i/steps+n[1]*offset);samples+=1
     if not any(poly.Contains(p.VECTOR2I(*(p.FromMM(v) for v in pt))) for poly in planes):gaps.append(pt)
 check('filled adjacent ground under oscillator corridors',not gaps)
 # Connected rear-layer supply islands must each contain just one bypass
 # capacitor, one IC supply pin and one through feed. Front distribution is
 # deliberately excluded so a direct neighbouring-pin bypass is detectable.
 nodes=[]
 for key,q in pads.items():
  if q.GetNetname()=='CC_VDD' and q.IsOnLayer(p.B_Cu):
   nodes.append((key,q.GetEffectiveShape(p.B_Cu)))
 for t in tracks:
  if t.GetNetname()!='CC_VDD':continue
  if t.GetClass()=='PCB_VIA':nodes.append(('via:'+t.m_Uuid.AsString(),t.GetEffectiveShape(p.B_Cu)))
  elif t.GetLayer()==p.B_Cu:nodes.append(('track:'+t.m_Uuid.AsString(),t.GetEffectiveShape(p.B_Cu)))
 graph={i:{j for j in range(len(nodes)) if nodes[i][1].Collide(nodes[j][1],1)} for i in range(len(nodes))}
 for ref,pin in {**BRANCHES,'C74':None}.items():
  reached={next(i for i,n in enumerate(nodes) if n[0]==ref+'.1')};todo=list(reached)
  while todo:
   for j in graph[todo.pop()]-reached:reached.add(j);todo.append(j)
  labels={nodes[i][0] for i in reached};expected={ref+'.1'}|({'U5.'+pin} if pin else set())
  check(ref+' independent rear bypass branch',{s for s in labels if not s.startswith(('via:','track:'))}==expected and sum(s.startswith('via:') for s in labels)==1)
 for ref in ['C11','C12','C61','C62','C69','C70','C71','C72','C73','C74','R11']:
  q=pads[ref+'.2'];check(ref+' local connected ground via',any(math.dist(xy(q.GetPosition()),xy(v.GetPosition()))<=1.35 for v in ground_vias))
 ep=pads['U5.21'];center=xy(ep.GetPosition());thermal=[v for v in tracks if v.GetClass()=='PCB_VIA' and abs(xy(v.GetPosition())[0]-center[0])<=1.1 and abs(xy(v.GetPosition())[1]-center[1])<=1.1]
 check('five connected thermal vias',len(thermal)==5 and all(v.GetNetname()=='GND' and v.m_Uuid.AsString() in ground_ids for v in thermal))
 check('EP copper retained and mask closed',ep.GetSize()==p.VECTOR2I(p.FromMM(2.7),p.FromMM(2.7)) and ep.IsOnLayer(p.B_Cu) and not ep.IsOnLayer(p.B_Mask) and not ep.IsOnLayer(p.B_Paste))
 apertures=[q for q in fps['U5'].Pads() if not q.GetNumber()]
 check('four reviewed mask and paste windows',len(apertures)==4 and all(q.IsOnLayer(p.B_Mask) and q.IsOnLayer(p.B_Paste) and q.GetShape()==p.PAD_SHAPE_RECT and q.GetSize()==p.VECTOR2I(p.FromMM(1),p.FromMM(1)) and abs(p.ToMM(q.GetLocalSolderMaskMargin())-.05)<1e-6 for q in apertures))
 for v in thermal:
  check('thermal via geometry and two-face tenting',v.GetWidth(p.F_Cu)==p.FromMM(.5) and v.GetDrillValue()==p.FromMM(.3) and v.GetFrontTentingMode()==p.TENTING_MODE_TENTED and v.GetBackTentingMode()==p.TENTING_MODE_TENTED)
  pos=xy(v.GetPosition());clearance=[]
  # Non-copper aperture pads use zero effective mask expansion in KiCad;
  # use the exported geometry, not the stored local margin.
  for q in apertures:
   a=xy(q.GetPosition());s=xy(q.GetSize());margin=p.ToMM(q.GetSolderMaskExpansion(p.B_Mask));clearance.append(math.hypot(max(abs(pos[0]-a[0])-s[0]/2-margin,0),max(abs(pos[1]-a[1])-s[1]/2-margin,0))-.15)
  check('thermal drill covered with nominal mask margin',bool(clearance) and min(clearance)>=.14999)
 return dict(passed=all(c['passed'] for c in checks),checks=checks,route_lengths_mm=lengths,reference_samples=samples,reference_gaps=gaps,qualification_open=['Qualify CC1101 oscillator startup, frequency, crystal drive and load capacitance on assembled boards across voltage and temperature.','Obtain assembler approval for four 1mm paste windows (54.9% EP coverage), 1mm mask windows and five 0.3mm component-side tented drills; nominal mask-to-drill margin is 0.15mm.','Validate filtered supply transient/noise performance, thermal joints and RF coexistence. Digital-interface timing and RF performance remain unqualified.'],fabrication_released=False)
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT;r=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')));(out/'cc1101-support-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
