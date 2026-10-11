#!/usr/bin/env python3
"""Stage component-side CC1101 matching and antenna copper."""
import csv,hashlib,json,shutil
from pathlib import Path
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-cc1101-rf')
PLACEMENTS={'L6':(126,39.3,0),'C63':(127.45,39,270),'L7':(127,36.35,90),'C66':(128.2,34.9,0),'C64':(129,37.5,0),'L8':(129,39,0),'L9':(131,38.9,0),'C65':(131.7,41.3,0),'L10':(130.3,40.3,180),'C67':(126.9,43.2,270),'C68':(127.5,41,0),'J21':(130.5,44.7,0)}
P=lambda a:p.VECTOR2I(*(p.FromMM(v) for v in a))
xy=lambda a:tuple(round(p.ToMM(v),5) for v in a)
def main():
 assert not (SRC/'cc1101-rf-routing.json').exists()
 shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".history",".git","*.lck","*.prl"))
 b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));before=geometry(b);fps={f.GetReference():f for f in b.GetFootprints()}
 for ref,(x,y,a) in PLACEMENTS.items():fps[ref].SetPosition(P((x,y)));fps[ref].SetOrientationDegrees(a)
 def pad(key):
  ref,pin=key.split('.');return xy(next(q for q in fps[ref].Pads() if q.GetNumber()==pin).GetPosition())
 def tr(net,pts,w=.2):
  for a,z in zip(pts,pts[1:]):
   if a==z:continue
   t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(w));t.SetLayer(p.B_Cu);t.SetNet(b.FindNet(net));b.Add(t)
 def via(pos):
  v=p.PCB_VIA(b);v.SetPosition(P(pos));v.SetWidth(p.FromMM(.5));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet('GND'));v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v)
 tr('CC_RF_P',[pad('U5.12'),(124.8,38.5),(125,38.3),pad('L5.1')])
 tr('CC_RF_N',[pad('U5.13'),(125.215,39),(125.515,39.3),pad('L6.1')])
 tr('CC_BAL_P',[pad('L5.2'),(127.45,38.3),pad('C63.1')])
 tr('CC_BAL_P',[(127.45,38.3),(127,38.2),pad('L7.1')])
 tr('CC_BAL_P',[(127,37.5),pad('C64.1')])
 tr('CC_SHUNT',[pad('L7.2'),(127,34.9),pad('C66.1')])
 tr('CC_BAL_N',[pad('L6.2'),(127.45,39.7),pad('C63.2')])
 tr('CC_BAL_N',[(127.45,39.7),(127.8,39.7),(128.5,39),pad('L8.1')])
 tr('CC_BAL_N',[(127.45,39.7),(127.02,40.13),pad('C68.1')])
 tr('CC_MATCH',[pad('C64.2'),(129.48,38.565),pad('L8.2'),pad('L9.1')])
 tr('CC_LPF',[pad('L9.2'),(131.6,39.015),(131.6,40.92),pad('C65.1')])
 tr('CC_LPF',[pad('L9.2'),(131,39.385),(131,40.085),pad('L10.1')])
 tr('CC_DC_BLOCK',[pad('L10.2'),(129,41.115),(129,41.8),(128.08,42.72),pad('C67.1')])
 tr('CC_RF_50R',[pad('C67.2'),(126.9,43.7),(127.9,44.7),pad('J21.1')],.34)
 for key,pos in [('C66.2',(129.4,34.9)),('C68.2',(127.98,41.8)),('C65.2',(132.1,42.1))]:tr('GND',[pad(key),pos],.3);via(pos)
 for y in (43.225,46.175):tr('GND',[(130.5,y),(132,y)],.4);via((132,y))
 for pos in [(128,36),(129,36.5),(132.2,39.8),(128,45.5)]:via(pos)
 for layer in (p.In1_Cu,p.In2_Cu,p.B_Cu):
  z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetZoneName('CC1101 RF return');z.SetLocalClearance(p.FromMM(.5 if layer==p.B_Cu else .2));z.SetMinThickness(p.FromMM(.2));z.SetAssignedPriority(6);z.SetPadConnection(p.ZONE_CONNECTION_FULL);poly=z.Outline();poly.NewOutline()
  for a in [(124.2,33.8),(132.5,33.8),(132.5,47.2),(124.2,47.2)]:poly.Append(P(a).x,P(a).y)
  for other in b.Zones():
   if not other.GetIsRuleArea() and other.GetLayer()==layer:poly.BooleanSubtract(other.Outline())
  b.Add(z)
 p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SRC/'handset.kicad_pro',OUT/'handset.kicad_pro')
 after=geometry(b);assert all(after['copper'][k]==v for k,v in before['copper'].items());assert all(after['footprints'][k]==v for k,v in before['footprints'].items() if k not in PLACEMENTS)
 spec=json.loads((OUT/'connectivity.json').read_text())
 for c in spec:
  if c['ref'] in PLACEMENTS:c.update(x=PLACEMENTS[c['ref']][0],y=PLACEMENTS[c['ref']][1],angle=PLACEMENTS[c['ref']][2])
 (OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
 with (OUT/'placement.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
 m=dict(source_board_sha256=hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),placements=PLACEMENTS,preserved_copper_items=len(before['copper']),added_copper_items=len(after['copper'])-len(before['copper']),fabrication_released=False)
 (OUT/'cc1101-rf-routing.json').write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
