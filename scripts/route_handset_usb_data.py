#!/usr/bin/env python3
"""Stage explicit USB differential paths; native DRC and independent checks gate installation."""
import hashlib,json,shutil
from pathlib import Path
import pcbnew as p
from sync_handset_schematic_rebuild import geometry
from handset_usb_power_path import route as power_path
p.SwigPyIterator.next=p.SwigPyIterator.__next__
SRC=Path('/tmp/handset-usb-data');OUT=Path('/tmp/handset-usb-routing')
ACTIVE=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
assert not (ACTIVE/'usb-data-update.json').exists(),'Already installed; preserve subsequent edits'
assert hashlib.sha256((ACTIVE/'handset.kicad_pcb').read_bytes()).hexdigest()==json.loads((SRC/'usb-data-update.json').read_text())['source_board_sha256'],'Staged source is stale'
shutil.copytree(SRC,OUT,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.history','.git','*.lck','*.prl'))
b=p.LoadBoard(str(SRC/'handset.kicad_pcb'));before=geometry(b)
# Move only the obstructing local VBUS T-junction to In1, leaving In2 as the
# reference beneath the bottom USB signal fanout. Both existing VBUS vias stay.
changed_power=[]
for t in b.GetTracks():
 if t.GetNetname()=='USB_VBUS' and t.GetLayer()==p.B_Cu:
  start=(round(p.ToMM(t.GetStart().x),4),round(p.ToMM(t.GetStart().y),4))
  end=(round(p.ToMM(t.GetEnd().x),4),round(p.ToMM(t.GetEnd().y),4))
  if start==(125.4,53.6) and end==(125.4,58.4):t.SetLayer(p.In1_Cu);t.SetEnd(p.VECTOR2I(p.FromMM(123.5),p.FromMM(53.6)));changed_power.append(t.m_Uuid.AsString())
  if start==(125.4,56.0) and end==(129.2125,56.0):t.SetStart(p.VECTOR2I(p.FromMM(128.5),p.FromMM(56)));changed_power.append(t.m_Uuid.AsString())
assert len(changed_power)==2
P=lambda xy:p.VECTOR2I(*[p.FromMM(v) for v in xy])
F,B=p.F_Cu,p.B_Cu
N,PLUS='USB_D_N','USB_D_P'
def tr(net,points,w=.29,layer=F):
 for a,z in zip(points,points[1:]):
  if a==z:continue
  t=p.PCB_TRACK(b);t.SetStart(P(a));t.SetEnd(P(z));t.SetWidth(p.FromMM(w));t.SetLayer(layer);t.SetNet(b.FindNet(net));b.Add(t)
def via(net,x,y):
 v=p.PCB_VIA(b);v.SetPosition(P((x,y)));v.SetWidth(p.FromMM(.5));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(F,B);v.SetNet(b.FindNet(net));b.Add(v)
via('USB_VBUS',128.5,56)
# Host termination and main pair.
tr('USB_HOST_D_N',[(91.98,49.25),(91.98,47.98),(96.74,47.98)],.2,B)
tr('USB_HOST_D_P',[(93.25,49.25),(93.25,48.65),(93.5,48.4),(93.75,48.4),(94,48.65),(94,49.185076),(94.25,49.435076),(94.5,49.185076),(94.5,48.65),(94.75,48.4),(95.8,48.4),(96.4,49),(96.49,49),(96.74,49.25)],.2,B)
tr(N,[(97.76,47.98),(98.47,47.98),(100.59,50.1),(106,50.1),(106.5,49.95)],.29,B)
tr(PLUS,[(97.76,49.25),(98.1,49.25),(98.1,51.9835),(98.6,52.4835),(103.2,52.4835),(103.8,51.8835),(103.8,51.2),(104.4,50.6),(106,50.6),(106.5,50.75)],.29,B)
via(N,106.5,49.95);via(PLUS,106.5,50.75)
tr(N,[(106.5,49.95),(107,50.1),(117,50.1),(118.9,52),(120.615,52)])
tr(PLUS,[(106.5,50.75),(107,50.6),(116.792893,50.6),(118.692893,52.5),(119.2,52.5)])
tr(PLUS,[(119.2,52.5),(120.615,52.5)],.18)
# External copper bridges the TI NC lands.
tr(N,[(120.615,52),(121.385,52)],.2)
tr(PLUS,[(120.615,52.5),(121.385,52.5)],.2)
# Join each polarity symmetrically so either Type-C orientation sees equal branches.
tr(PLUS,[(126.32,55.25),(125.3,55.25),(125.3,55.75),(125.3,56.25),(126.32,56.25)],.15)
tr(PLUS,[(125.3,55.75),(124.8,55.25),(124.6,55.25)],.15)
tr(N,[(126.32,55.75),(127.15,55.75),(127.15,56.25),(127.15,56.75),(126.32,56.75)],.15)
tr(N,[(127.15,56.25),(127.4,56.25)],.15)
via(PLUS,124.6,55.25);via(N,127.4,56.25)
tr(N,[(127.4,56.25),(127.4,55.25),(126.8,54.65),(124.3,54.65),(123.5,53.85),(123.5,52)],.29,B)
tr(PLUS,[(124.6,55.25),(123.9,55.25),(122.8,54.15),(122.8,52.3)],.29,B)
via(N,123.5,52);via(PLUS,122.8,52.3)
tr(N,[(123.5,52),(123.2,51.7),(121.685,51.7),(121.385,52)],.2)
tr(PLUS,[(122.8,52.3),(122.6,52.5),(121.385,52.5)],.2)
# Local reference copper on both inner layers, excluding existing zone outlines.
for layer in [p.In1_Cu,p.In2_Cu]:
 z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(p.FromMM(.2));z.SetMinThickness(p.FromMM(.15));z.SetZoneName('USB data reference');z.SetAssignedPriority(8);z.SetPadConnection(p.ZONE_CONNECTION_FULL)
 poly=z.Outline();poly.NewOutline()
 for x,y in [(90.5,46.5),(129.2,46.5),(129.2,59),(90.5,59)]:poly.Append(p.FromMM(x),p.FromMM(y))
 for existing in b.Zones():
  if existing.GetLayer()==layer:poly.BooleanSubtract(existing.Outline())
 b.Add(z)
for x,y in [(106.5,49.1),(107.4,51.6),(128.2,54.75),(129.4,54.8),(124.2,51.5),(124.4,52.8)]:via('GND',x,y)
# Identify by layer because iteration order is not an API contract.
bridge=next(t for t in b.GetTracks() if t.m_Uuid.AsString() in changed_power and t.GetLayer()==p.In1_Cu)
path=power_path(b,(125.4,53.6),(125.4,58.4));bridge.SetStart(P(path[0]));bridge.SetEnd(P(path[1]));tr('USB_VBUS',path[1:],.6,p.In1_Cu)
tr('USB_VBUS',power_path(b,(125.4,58.4),(128.5,56)),.6,p.In1_Cu)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(OUT/'handset.kicad_pcb'),b)
after=geometry(b);assert before['footprints']==after['footprints'];assert all(after['copper'][k]==v for k,v in before['copper'].items() if k not in changed_power)
print('Staged',OUT,'added',len(after['copper'])-len(before['copper']),'items')
# Record the chosen nominal stack in native KiCad data. Published rounded copper/
# dielectric entries total 1.5862 mm; board nominal remains 1.6 mm pending fab DFM.
from cad_sexpr import parse,dump,child
boardfile=OUT/'handset.kicad_pcb';tree=parse(boardfile.read_text());setup=child(tree,'setup')
stack='''(stackup
 (layer "F.SilkS" (type "Top Silk Screen"))
 (layer "F.Paste" (type "Top Solder Paste"))
 (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01524) (epsilon_r 3.8))
 (layer "F.Cu" (type "copper") (thickness 0.035))
 (layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4))
 (layer "In1.Cu" (type "copper") (thickness 0.0152))
 (layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.6))
 (layer "In2.Cu" (type "copper") (thickness 0.0152))
 (layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4))
 (layer "B.Cu" (type "copper") (thickness 0.035))
 (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01524) (epsilon_r 3.8))
 (layer "B.Paste" (type "Bottom Solder Paste"))
 (layer "B.SilkS" (type "Bottom Silk Screen"))
 (dielectric_constraints yes))'''
assert child(setup,'stackup') is None;setup.insert(1,parse(stack));boardfile.write_text(dump(tree)+'\n')
b=p.LoadBoard(str(boardfile));p.SaveBoard(str(boardfile),b)
final_geometry=geometry(b)
assert before['footprints']==final_geometry['footprints']
assert all(final_geometry['copper'][k]==v for k,v in before['copper'].items() if k not in changed_power)
project=json.loads((OUT/'handset.kicad_pro').read_text());netsettings=project['net_settings']
netsettings['classes'].append(dict(name='USB data',priority=0,clearance=.15,track_width=.29,via_diameter=.5,via_drill=.3,diff_pair_width=.29,diff_pair_gap=.21,diff_pair_via_gap=.25))
netsettings['netclass_patterns']=[dict(netclass='USB data',pattern=net) for net in (N,PLUS)]
(OUT/'handset.kicad_pro').write_text(json.dumps(project,indent=2)+'\n')
manifest=json.loads((OUT/'usb-data-update.json').read_text())
manifest.update(final_board_sha256=hashlib.sha256(boardfile.read_bytes()).hexdigest(),modified_existing_copper_ids=changed_power,preserved_copper_items=len(before['copper'])-len(changed_power),added_copper_items=len(after['copper'])-len(before['copper']),existing_footprints_preserved=True,stackup='JLC04161H-7628',stackup_source='https://jlcpcb.com/impedance',nominal_board_thickness_mm=1.6,published_copper_dielectric_sum_mm=1.5862,stackup_status='Design target; fabricator tolerance/impedance approval pending',pair_trunk_width_mm=.29,pair_trunk_gap_mm=.21,nominal_differential_target_ohms=90,impedance_tolerance_percent=10,return_reference_layers=['In1.Cu','In2.Cu'],qualification='Nominal cross-section estimate only. Local breakouts, uncoupled tuning, three transitions per leg, ESD, termination and USB eye remain unqualified.')
(OUT/'usb-data-update.json').write_text(json.dumps(manifest,indent=2)+'\n')
with (OUT/'usb-data-bom.csv').open('w') as stream:
 stream.write('Reference,Manufacturer,MPN,Value,Footprint,Qualification\n')
 for ref in ('R88','R89'):stream.write(ref+',Yageo,RC0402FR-0722RL,22 ohm 1%,Resistor_SMD:R_0402_1005Metric,Initial termination; qualify USB electrical performance\n')
