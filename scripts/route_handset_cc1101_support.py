#!/usr/bin/env python3
"""Stage CC1101 crystal, separate bypass branches and exposed-pad returns."""
import csv,hashlib,json,shutil
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,dump,child,children,Q
from sync_handset_schematic_rebuild import geometry
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'hardware/handset-rev-a/generated';OUT=Path('/tmp/handset-cc1101-support')
FP='CC1101_RGP20_MaskedThermalVias';LIBID='Handset:'+FP
PLACEMENTS={'Y2':(123.4,32.4,0,'B'),'C61':(121.5,30.0,0,'B'),'C62':(126.5,33.4,0,'B'),
 'C11':(117.8,38.0,180,'B'),'C12':(117.8,39.4,180,'B'),'C69':(122.1,35.1,90,'B'),
 'C70':(125,37,0,'B'),'C71':(125.1,40.8,0,'B'),'C72':(124.5,42.4,0,'B'),
 'C73':(121,42.5,180,'B'),'R11':(122.7,42.9,270,'B'),
 'L11':(120,45,0,'F'),'R12':(124,45.2,0,'F'),
 'L5':(126,38.3,0,'B'),'L6':(126,39.7,0,'B'),'C66':(128,32.1,0,'B'),'C67':(126,43.6,0,'B'),'C68':(127.6,40.4,90,'B')}
FEEDS={'C12':(118.28,40.3),'C69':(122.8,35.58),'C70':(123.8,37.25),'C71':(124.62,41.55),'C72':(124.02,43.2),'C73':(121.48,43.2),'C74':(121.2,47.25)}
RETURNS={'C11':(117.85,38.7),'C12':(116.5,40.15),'C69':(122.8,34.62),'C70':(126.2,37),'C71':(126.3,40.8),'C72':(125.7,42.4),'C73':(120.52,41.85),'C74':(122,45.52),'C61':(123.0,30.0),'C62':(127.65,33.4),'R11':(122.7,44.1)}
THERMAL=[(121.5,39),(120.65,39),(122.35,39),(121.5,38.15),(121.5,39.85)]
P=lambda a:p.VECTOR2I(*(p.FromMM(v) for v in a))
xy=lambda a:(round(p.ToMM(a.x),5),round(p.ToMM(a.y),5))

def mask_pattern(f,side):
 for q in children(f,'pad'):
  if q[1]=='21':child(q,'layers')[:]=['layers',Q(side+'.Cu')]
  elif q[1]=='':
   at=child(q,'at');at[1:3]=[.8 if float(v)>0 else -.8 for v in at[1:3]]
   q[3]='rect';child(q,'size')[1:]=[1,1];child(q,'layers')[:]=['layers',Q(side+'.Paste'),Q(side+'.Mask')]
   q[:]=[v for v in q if not (isinstance(v,list) and v[0] in ('roundrect_rratio','solder_mask_margin'))]
   q.append(['solder_mask_margin',.05])

def main():
 assert not (SRC/'cc1101-support-routing.json').exists(),'Already installed'
 shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.history','.git','*.lck','*.prl'))
 original=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(original)
 tree=parse((SRC/'handset.kicad_pcb').read_text());f=next(f for f in children(tree,'footprint') if any(v[1]=='Reference' and v[2]=='U5' for v in children(f,'property')));f[1]=Q(LIBID);mask_pattern(f,'B')
 (OUT/'handset.kicad_pcb').write_text(dump(tree)+'\n')
 fp=parse(Path('/usr/share/kicad/footprints/Package_DFN_QFN.pretty/Texas_RGP0020D_VQFN-20-1EP_4x4mm_P0.5mm_EP2.7x2.7mm.kicad_mod').read_text());fp[1]=Q(FP);mask_pattern(fp,'F')
 child(fp,'descr')[1]=Q('CC1101 RGP20 copper lands; four 1mm paste / 1mm mask windows for five component-side tented thermal vias. Assembly qualification required.')
 (OUT/'Handset.pretty'/f'{FP}.kicad_mod').write_text(dump(fp)+'\n')
 sch=parse((SRC/'cc-radio.kicad_sch').read_text());sym=next(s for s in children(sch,'symbol') if any(v[1]=='Reference' and v[2]=='U5' for v in children(s,'property')))
 next(v for v in children(sym,'property') if v[1]=='Footprint')[2]=Q(LIBID);(OUT/'cc-radio.kicad_sch').write_text(dump(sch)+'\n')
 b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()}
 for ref,(x,y,angle,side) in PLACEMENTS.items():
  f=fps[ref];layer=p.B_Cu if side=='B' else p.F_Cu
  if f.GetLayer()!=layer:f.Flip(f.GetPosition(),False)
  f.SetPosition(P((x,y)));f.SetOrientationDegrees(angle);f.Reference().SetLayer(p.B_Fab if side=='B' else p.F_Fab)
 def pad(key):
  ref,pin=key.split('.');return xy(next(q for q in fps[ref].Pads() if q.GetNumber()==pin).GetPosition())
 def tr(net,points,width=.2,layer=p.B_Cu):
  for a,z in zip(points,points[1:]):
   if a==z:continue
   t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)
 def via(net,pos):
  v=p.PCB_VIA(b);v.SetPosition(P(pos));v.SetWidth(p.FromMM(.5));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v)
 # No signal vias in either oscillator leg.
 tr('CC_X1',[pad('U5.8'),(121.5,36.25),(121.35,36.1),(121.35,35.45),(120.9,35.0),(120.9,31.525),pad('Y2.1')])
 tr('CC_X1',[(120.9,31.525),pad('C61.1')])
 tr('CC_X2',[pad('U5.10'),(122.5,36.5),(123.7,36.5),(124.55,35.65),pad('Y2.3')])
 tr('CC_X2',[pad('Y2.3'),(125.3,33.275),(125.425,33.4),pad('C62.1')])
 tr('CC_DCOUPL',[pad('U5.5'),pad('C11.1')])
 tr('CC_RBIAS',[pad('U5.17'),(122,41.69),pad('R11.1')],.15)
 # Six separate rear-layer bypass branches; front distribution reaches each
 # capacitor through its own via on the capacitor side of the IC connection.
 branches={'C12':('4',[(118.8,38.5),(118.28,39.02)]),'C69':('9',[(122,36.0)]),
  'C70':('11',[(124.2,38),(124.52,37.68)]),'C71':('14',[(124.62,39.5)]),
  'C72':('15',[(123.9,40.4375),(123.9,42.28)]),'C73':('18',[(121.5,42.38)])}
 for ref,(pin,points) in branches.items():tr('CC_VDD',[pad('U5.'+pin)]+points+[pad(ref+'.1')])
 for ref,pos in FEEDS.items():tr('CC_VDD',[pos,pad(ref+'.1')],.25);via('CC_VDD',pos)
 # A dedicated filtered front-layer supply distribution avoids routing inside
 # the inner reference planes under the radio, crystal and matching circuit.
 tr('+3V3',[(114.9,46.8),(119.515,46.8),pad('L11.1')],.3,p.F_Cu)
 tr('CC_VDD',[pad('L11.2'),(120.485,44.195),(121.48,43.2),(124.6,43.2),(124.6,35.58),FEEDS['C69']],.3,p.F_Cu)
 tr('CC_VDD',[(124.6,37.25),FEEDS['C70']],.3,p.F_Cu)
 tr('CC_VDD',[(124.6,41.55),FEEDS['C71']],.3,p.F_Cu)
 tr('CC_VDD',[FEEDS['C12'],(119.7,41.72),(119.7,43.2),FEEDS['C73']],.3,p.F_Cu)
 tr('CC_VDD',[pad('L11.2'),(121.2,45.715),FEEDS['C74']],.3,p.F_Cu)
 for ref,pos in RETURNS.items():tr('GND',[pad(ref+'.2'),pos],.25);via('GND',pos)
 for key,pos in [('Y2.2',(125.65,31.525)),('Y2.4',(121.45,34.4))]:tr('GND',[pad(key),pos],.3);via('GND',pos)
 # Thermal vias sit in the masked cross between four paste/mask windows.
 for pos in THERMAL:via('GND',pos)
 tr('GND',[pad('U5.16'),(122.5,39)],.25);tr('GND',[pad('U5.19'),(121,39)],.25)
 for layer in (p.In1_Cu,p.In2_Cu):
  z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetZoneName('CC1101 support return');z.SetLocalClearance(p.FromMM(.2));z.SetMinThickness(p.FromMM(.2));z.SetAssignedPriority(7);z.SetPadConnection(p.ZONE_CONNECTION_FULL)
  poly=z.Outline();poly.NewOutline()
  for a in [(117,28.7),(129,28.7),(129,48),(119.8,48),(119.8,42),(117,42)]:poly.Append(P(a).x,P(a).y)
  for other in b.Zones():
   if not other.GetIsRuleArea() and other.GetLayer()==layer:poly.BooleanSubtract(other.Outline())
  b.Add(z)
 # Local component-side ground for the EP and its ground pins.
 z=p.ZONE(b);z.SetLayer(p.B_Cu);z.SetNet(b.FindNet('GND'));z.SetZoneName('CC1101 exposed pad');z.SetLocalClearance(p.FromMM(.15));z.SetMinThickness(p.FromMM(.15));z.SetAssignedPriority(7);z.SetPadConnection(p.ZONE_CONNECTION_FULL)
 poly=z.Outline();poly.NewOutline()
 for a in [(120.15,37.65),(122.85,37.65),(122.85,41.45),(120.8,41.45),(120.15,40.35)]:poly.Append(P(a).x,P(a).y)
 b.Add(z);p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b);shutil.copy2(SRC/'handset.kicad_pro',OUT/'handset.kicad_pro')
 after=geometry(b);assert all(after['copper'][k]==v for k,v in before['copper'].items());assert all(after['footprints'][k]==v for k,v in before['footprints'].items() if k not in PLACEMENTS and k!='U5')
 spec=json.loads((OUT/'connectivity.json').read_text())
 for c in spec:
  if c['ref']=='U5':c['footprint']=LIBID
  if c['ref'] in PLACEMENTS:
   f=fps[c['ref']];c.update(x=xy(f.GetPosition())[0],y=xy(f.GetPosition())[1],side='B' if f.GetLayer()==p.B_Cu else 'F',angle=f.GetOrientationDegrees())
 (OUT/'connectivity.json').write_text(json.dumps(spec,indent=2)+'\n')
 with (OUT/'placement.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=['ref','value','footprint','x','y','side','angle','sheet'],extrasaction='ignore');w.writeheader();w.writerows(spec)
 report=dict(source_board_sha256=hashlib.sha256((SRC/'handset.kicad_pcb').read_bytes()).hexdigest(),final_board_sha256=hashlib.sha256((OUT/'handset.kicad_pcb').read_bytes()).hexdigest(),placements=PLACEMENTS,modified_footprints=['U5'],preserved_copper_items=len(before['copper']),added_copper_items=len(after['copper'])-len(before['copper']),preserved_footprints=len(before['footprints'])-len(PLACEMENTS)-1,feed_vias=FEEDS,ground_vias=RETURNS,thermal_vias=THERMAL,fabrication_released=False)
 (OUT/'cc1101-support-routing.json').write_text(json.dumps(report,indent=2)+'\n');print(OUT)
if __name__=='__main__':main()
