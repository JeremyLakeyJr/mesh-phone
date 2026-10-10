#!/usr/bin/env python3
"""Check switched RF continuity, transitions and ground reference; not RF sign-off."""
import json,math,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={'SX_TX_MATCH':'U36.8 C99.1','SX_TX_AC':'C99.2 U37.1','SX_RX_MATCH':'U36.6 C100.1','SX_RX_AC':'C100.2 U37.3','SX_ANT_AC':'U37.5 C98.1','LORA_RF_50R':'C98.2 J20.1','SX_RF_SW':'U4.12 R91.1','SX_SWITCH_CTRL':'R91.2 U37.6 C96.1 R93.1','SX_SWITCH_VDD':'R92.2 U37.4 C97.1','+3V3':'U4.10 R92.1','GND':'U1.1 U37.2 C96.2 C97.2 R93.2 J20.2'}
RF={'SX_TX_MATCH':1,'SX_TX_AC':0,'SX_RX_MATCH':1,'SX_RX_AC':0,'SX_ANT_AC':0,'LORA_RF_50R':1}

def check_board(b):
 b.BuildConnectivity();pads={}
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.GetNumber():pads.setdefault(f.GetReference()+'.'+q.GetNumber(),[]).append(q)
 checks=[];lengths={};gaps=[];samples=0;exempt=0;transitions=[]
 def check(name,value):checks.append(dict(check=name,passed=bool(value)))
 for net,names in GROUPS.items():
  entries=[q for key in names.split() for q in pads[key]];seed=entries[0]
  connected=list(b.GetConnectivity().GetConnectedItems(seed));ids={q.m_Uuid.AsString() for q in connected}|{seed.m_Uuid.AsString()}
  check(net+' full pad continuity',all(q.GetNetname()==net and q.m_Uuid.AsString() in ids for q in entries) and all(q.GetNetname()==net for q in connected))
 fps={f.GetReference():f for f in b.GetFootprints()}
 for ref in ['U37','C98','C99','C100','R91','R92','R93','C96','C97']:check(ref+' front layer',fps[ref].GetLayer()==p.F_Cu)
 ground_anchor=pads['U1.1'][0];ground_ids={q.m_Uuid.AsString() for q in b.GetConnectivity().GetConnectedItems(ground_anchor)}|{ground_anchor.m_Uuid.AsString()}
 grounds=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND' and t.m_Uuid.AsString() in ground_ids]
 planes={layer:[z.GetFilledPolysList(layer) for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname()=='GND' and z.IsOnLayer(layer)] for layer in (p.In1_Cu,p.In2_Cu)}
 xy=lambda a:(p.ToMM(a.x),p.ToMM(a.y))
 for net,wanted in RF.items():
  copper=[t for t in b.GetTracks() if t.GetNetname()==net];vias=[t for t in copper if t.GetClass()=='PCB_VIA'];tracks=[t for t in copper if t.GetClass()=='PCB_TRACK']
  check(net+' signal via count',len(vias)==wanted)
  check(net+' external copper only',bool(tracks) and all(t.GetLayer() in (p.F_Cu,p.B_Cu) for t in tracks))
  check(net+' reviewed width range',all(round(p.ToMM(t.GetWidth()),4) in (.15,.2,.34) for t in tracks))
  lengths[net]=round(sum(p.ToMM(t.GetLength()) for t in tracks),4)
  check(net+' bounded copper length',0<lengths[net]<(12 if net=='LORA_RF_50R' else 7))
  for v in vias:
   pos=xy(v.GetPosition());near=min((math.dist(pos,xy(g.GetPosition())) for g in grounds),default=1e9)
   check(net+' close connected transition return',near<=1.25)
   check(net+' through via geometry/tenting',v.GetViaType()==p.VIATYPE_THROUGH and v.TopLayer()==p.F_Cu and v.BottomLayer()==p.B_Cu and v.GetWidth(p.F_Cu)==p.FromMM(.5) and v.GetDrillValue()==p.FromMM(.3) and v.GetFrontTentingMode()==p.TENTING_MODE_TENTED and v.GetBackTentingMode()==p.TENTING_MODE_TENTED)
   # A solder-masked nominal drill outside all numbered lands avoids ordinary
   # open via-in-pad. Process tolerances still require fabrication review.
   land_gaps=[]
   for items in pads.values():
    for q in items:
     box=q.GetBoundingBox();xmin,ymin=p.ToMM(box.GetX()),p.ToMM(box.GetY());xmax,ymax=p.ToMM(box.GetRight()),p.ToMM(box.GetBottom())
     land_gaps.append(math.hypot(max(xmin-pos[0],0,pos[0]-xmax),max(ymin-pos[1],0,pos[1]-ymax))-.15)
   check(net+' transition drill outside lands',min(land_gaps)>=.15-1e-5)
   transitions.append(dict(net=net,position_mm=pos,nearest_ground_via_mm=round(near,4),minimum_nominal_land_gap_mm=round(min(land_gaps),4)))
  for t in tracks:
   a,z=xy(t.GetStart()),xy(t.GetEnd());d=math.dist(a,z)
   if not d:continue
   n=(-(z[1]-a[1])/d,(z[0]-a[0])/d);steps=max(1,math.ceil(d/.1));layer=p.In1_Cu if t.GetLayer()==p.F_Cu else p.In2_Cu
   for i in range(steps+1):
    for offset in (0,-p.ToMM(t.GetWidth())/2-.1,p.ToMM(t.GetWidth())/2+.1):
     pt=(a[0]+(z[0]-a[0])*i/steps+n[0]*offset,a[1]+(z[1]-a[1])*i/steps+n[1]*offset);samples+=1
     if any(poly.Contains(p.VECTOR2I(p.FromMM(pt[0]),p.FromMM(pt[1]))) for poly in planes[layer]):continue
     # Only the explicit same-net transition's ordinary 0.2mm plane antipad
     # is exempt; all other gaps remain failures.
     if any(math.dist(pt,xy(v.GetPosition()))<=.46 for v in vias):exempt+=1;continue
     gaps.append(dict(net=net,layer=b.GetLayerName(layer),position_mm=pt))
 check('adjacent filled ground under RF corridors except transition antipads',not gaps)
 return dict(passed=all(c['passed'] for c in checks),checks=checks,route_lengths_mm=lengths,signal_transitions=transitions,reference_samples=samples,via_antipad_exempt_samples=exempt,reference_gaps=gaps,physical_pads=sum(len(pads[key]) for names in GROUPS.values() for key in names.split()),qualification_open=[
  'Qualify all RF layer transitions, neck-downs, bends, coplanar clearance and 100pF DC blocks against the selected stackup; nominal 0.34mm trunks are screening targets only.',
  'Validate switch timing, DC isolation, insertion loss, conducted transmit power/harmonics, receive sensitivity, antenna match and coexistence on assembled hardware.',
  'Confirm via drill/tenting tolerances, reference returns and the revised 3V3 feed under load with the fabricator and hardware review.'],fabrication_released=False)
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT;r=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')));(out/'sx1262-switch-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
