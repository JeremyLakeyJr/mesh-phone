#!/usr/bin/env python3
"""Independent IPD return/via geometry and scoped fabrication-rule checks."""
import json,math,sys
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,child,children
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
PINS=('2','5','7','9','10')

def check_board(b):
 b.BuildConnectivity();fps={f.GetReference():f for f in b.GetFootprints()}
 pads={q.GetNumber():q for q in fps['U36'].Pads()};anchor=next(q for q in fps['U1'].Pads() if q.GetNumber()=='1')
 connected={q.m_Uuid.AsString() for q in b.GetConnectivity().GetConnectedItems(anchor)}|{anchor.m_Uuid.AsString()}
 checks=[]
 def check(name,passed):checks.append(dict(check=name,passed=bool(passed)))
 via_list=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetDrillValue()<p.FromMM(.3)]
 check('exactly five RF small-hole vias',len(via_list)==5)
 xy=lambda a:(p.ToMM(a.x),p.ToMM(a.y))
 records=[];matched=[]
 for pin in PINS:
  q=pads[pin]
  check('U36.'+pin+' established-ground continuity',q.GetNetname()=='GND' and q.m_Uuid.AsString() in connected)
  near=sorted(via_list,key=lambda v:math.dist(xy(v.GetPosition()),xy(q.GetPosition())))
  distance=math.dist(xy(near[0].GetPosition()),xy(q.GetPosition())) if near else float('inf')
  check('U36.'+pin+' via within 0.65mm',distance<=.65)
  if near and distance<=.65:matched.append(near[0].m_Uuid.AsString())
 check('separate nearest via for every ground land',len(set(matched))==5)
 for v in via_list:
  pos=xy(v.GetPosition());r=p.ToMM(v.GetWidth(p.B_Cu))/2
  valid=(v.GetNetname()=='GND' and v.GetDrillValue()==p.FromMM(.2) and v.GetWidth(p.B_Cu)==p.FromMM(.45)
         and v.GetViaType()==p.VIATYPE_THROUGH and v.TopLayer()==p.F_Cu and v.BottomLayer()==p.B_Cu
         and v.GetFrontTentingMode()==p.TENTING_MODE_TENTED and v.GetBackTentingMode()==p.TENTING_MODE_TENTED
         and 112.0<=pos[0]-r and pos[0]+r<=115.8 and 40.7<=pos[1]-r and pos[1]+r<=42.7
         and v.m_Uuid.AsString() in connected)
  check('RF via '+str(pos)+' drill/land/tenting/region/ground',valid)
  gaps=[]
  for q in pads.values():
   box=q.GetBoundingBox();xmin,ymin=p.ToMM(box.GetX()),p.ToMM(box.GetY());xmax,ymax=p.ToMM(box.GetRight()),p.ToMM(box.GetBottom())
   gap=math.hypot(max(xmin-pos[0],0,pos[0]-xmax),max(ymin-pos[1],0,pos[1]-ymax))-p.ToMM(v.GetDrillValue())/2
   gaps.append(gap)
  check('RF drill '+str(pos)+' nominal land gap >=0.15mm',min(gaps)>=.15-1e-5)
  records.append(dict(position_mm=pos,drill_mm=p.ToMM(v.GetDrillValue()),diameter_mm=p.ToMM(v.GetWidth(p.B_Cu)),minimum_nominal_land_gap_mm=round(min(gaps),4)))
 zones=[z for z in b.Zones() if z.GetZoneName()=='SX1262 IPD ground' and z.GetLayer()==p.B_Cu and z.GetNetname()=='GND' and not z.GetIsRuleArea()]
 check('one local back-layer ground zone',len(zones)==1)
 check('local ground zone reaches all five via centers',len(zones)==1 and len(via_list)==5 and all(zones[0].GetFilledPolysList(p.B_Cu).Contains(v.GetPosition()) for v in via_list))
 return dict(passed=all(c['passed'] for c in checks),checks=checks,vias=records,
  qualification_open=['Validate detailed IPD ground/via placement and harmonic attenuation against the Johanson reference; continuity is not RF qualification.',
   'Confirm 0.2mm finished-hole/tenting process and stackup with the fabricator; qualify the rerouted 0.5mm 3V3 feed under load.',
   'Finish RF switch/DC-block/antenna copper and validate line transitions, matching, conducted power/harmonics and sensitivity.'],fabrication_released=False)

def check_rules(out):
 errors=[]
 cfg=json.loads((out/'handset.kicad_pro').read_text());pro=cfg['board']['design_settings']['rules']
 for key,value in {'min_through_hole_diameter':.2,'min_via_diameter':.45,'min_via_annular_width':.1,'min_hole_clearance':.25,'min_hole_to_hole':.25,'min_clearance':.15}.items():
  if pro.get(key)!=value:errors.append(key+' fabrication minimum')
 ns=cfg['net_settings'];classes=[c for c in ns['classes'] if c['name']=='RF 50 ohm target']
 if len(classes)!=1 or classes[0].get('track_width')!=.34 or classes[0].get('clearance')!=.15:errors.append('downstream RF line-width target')
 members={v['pattern'] for v in ns['netclass_patterns'] if v['netclass']=='RF 50 ohm target'}
 if members!={'SX_TX_MATCH','SX_TX_AC','SX_RX_MATCH','SX_RX_AC','SX_ANT_AC','LORA_RF_50R'}:errors.append('RF impedance net-class scope')
 path=out/'handset.kicad_dru'
 if not path.exists():return errors+['custom rules missing; general minimums would be lost']
 tree=parse('('+'\n'.join(line for line in path.read_text().splitlines() if not line.lstrip().startswith('#'))+')')
 expected=[['version','1'],
  ['rule','General drilled holes',['constraint','hole_size',['min','0.3mm']]],
  ['rule','General vias',['condition',"A.Type == 'Via'"],['constraint','via_diameter',['min','0.5mm']]],
  ['rule','SX1262 RF ground vias',['condition',"A.Type == 'Via' && A.NetName == 'GND' && A.enclosedByArea('SX1262 RF grounding')"],
   ['constraint','hole_size',['min','0.2mm'],['max','0.2mm']],['constraint','via_diameter',['min','0.45mm'],['max','0.45mm']]]]
 if tree!=expected:errors.append('custom via rules/order differ from reviewed scope')
 board=parse((out/'handset.kicad_pcb').read_text())
 areas=[z for z in children(board,'zone') if child(z,'name') and child(z,'name')[1]=='SX1262 RF grounding']
 if len(areas)!=1:errors.append('RF grounding rule area missing/duplicated')
 else:
  z=areas[0];pts=children(child(child(z,'polygon'),'pts'),'xy')
  if {(float(a[1]),float(a[2])) for a in pts}!={(112.0,40.7),(115.8,40.7),(115.8,42.7),(112.0,42.7)} or not child(z,'keepout'):errors.append('RF rule area extent/type')
 return errors

def inspect(out):
 r=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')));r['rule_failures']=check_rules(out);r['passed'] &= not r['rule_failures'];return r
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
 r=inspect(out);(out/'sx1262-rf-ground-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
