#!/usr/bin/env python3
"""Independent TCXO netlist, land-pattern, copper and reference-plane checks."""
import copy,json,math,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from cad_sexpr import parse,child,children
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
GROUPS={
 'SX_TCXO_PWR':'U4.6 Y3.4 C94.1',
 'SX_TCXO_OUT':'Y3.3 R90.1',
 'SX_TCXO_COUPLED':'R90.2 C95.1',
 'SX_XTA':'C95.2 U4.3',
 'GND':'U1.1 U4.5 Y3.1 Y3.2 C94.2',
}
PARTS={
 'Y3':('32MHz TCXO 0.5ppm temp','ECS-TXO-32CSMV-320-AN-TR'),
 'R90':('220R 1%','RC0402FR-07220RL'),
 'C94':('100nF 10% X7R 16V','GRM155R71C104KA88D'),
 'C95':('10pF 5% C0G 50V','GRM1555C1H100JA01D'),
}
CLOCK_NETS=('SX_TCXO_OUT','SX_TCXO_COUPLED','SX_XTA')

def circuit_checks(nets,parts):
 errors=[]
 for net,names in GROUPS.items():
  for name in names.split():
   if nets.get(name)!=net:errors.append(name+' net')
  if net!='GND' and {name for name,value in nets.items() if value==net}!=set(names.split()):errors.append(net+' membership')
 if not nets.get('U4.4','').startswith('unconnected-('):errors.append('XTB must be NC')
 for ref,wanted in PARTS.items():
  if parts.get(ref)!=wanted:errors.append(ref+' value/MPN')
 return errors

def check_board(board):
 board.BuildConnectivity();pads={}
 for f in board.GetFootprints():
  for q in f.Pads():pads.setdefault(f.GetReference()+'.'+q.GetNumber(),[]).append(q)
 checks=[]
 def check(name,passed):checks.append(dict(check=name,passed=bool(passed)))
 for net,names in GROUPS.items():
  entries=[q for name in names.split() for q in pads[name]];seed=entries[0]
  connected=list(board.GetConnectivity().GetConnectedItems(seed))
  ids={q.m_Uuid.AsString() for q in connected}|{seed.m_Uuid.AsString()}
  check(net+' physical continuity',all(q.GetNetname()==net and q.m_Uuid.AsString() in ids for q in entries) and all(q.GetNetname()==net for q in connected))
 check('XTB isolated NC',pads['U4.4'][0].GetNetname().startswith('unconnected-(') and not any(t.GetNetname()==pads['U4.4'][0].GetNetname() for t in board.GetTracks()))
 planes=[z.GetFilledPolysList(p.In2_Cu) for z in board.Zones() if z.GetNetname()=='GND' and z.IsOnLayer(p.In2_Cu)]
 missing=[];samples=0;length=0
 for net in CLOCK_NETS:
  copper=[t for t in board.GetTracks() if t.GetNetname()==net]
  check(net+' back layer without vias',bool(copper) and all(t.GetClass()=='PCB_TRACK' and t.GetLayer()==p.B_Cu for t in copper))
  for t in copper:
   if t.GetClass()!='PCB_TRACK':continue
   a=(p.ToMM(t.GetStart().x),p.ToMM(t.GetStart().y));z=(p.ToMM(t.GetEnd().x),p.ToMM(t.GetEnd().y))
   distance=math.dist(a,z);length+=distance
   if not distance:continue
   normal=(-(z[1]-a[1])/distance,(z[0]-a[0])/distance)
   steps=max(1,math.ceil(distance/.1))
   for i in range(steps+1):
    for offset in (0,-p.ToMM(t.GetWidth())/2-.1,p.ToMM(t.GetWidth())/2+.1):
     point=(a[0]+(z[0]-a[0])*i/steps+normal[0]*offset,a[1]+(z[1]-a[1])*i/steps+normal[1]*offset);samples+=1
     if not any(poly.Contains(p.VECTOR2I(p.FromMM(point[0]),p.FromMM(point[1]))) for poly in planes):missing.append(point)
 check('clock copper length below 10mm',0<length<10)
 check('filled In2 ground under clock corridor',not missing)
 return dict(passed=all(c['passed'] for c in checks),checks=checks,physical_pads=14,
  clock_trace_length_mm=round(length,3),reference_samples=samples,reference_gaps=missing,fabrication_released=False)

def inspect(out):
 xml=ET.parse(out/'netlist.xml').getroot()
 nets={node.get('ref')+'.'+node.get('pin'):net.get('name') for net in xml.findall('./nets/net') for node in net.findall('node')}
 parts={c.get('ref'):(c.findtext('value'),c.findtext('fields/field[@name="MPN"]')) for c in xml.findall('./components/comp')}
 errors=circuit_checks(nets,parts);negative=[]
 for key,value in [('Y3.1','SX_TCXO_PWR'),('U4.4','GND'),('Y3.4','+3V3'),('C95.2','GND')]:
  bad=copy.deepcopy(nets);bad[key]=value
  negative.append(dict(mutation=key+' -> '+value,rejected=bool(circuit_checks(bad,parts))))
 bad=copy.deepcopy(parts);bad['C95']=('100nF',PARTS['C95'][1]);negative.append(dict(mutation='wrong coupling capacitance',rejected=bool(circuit_checks(nets,bad))))
 footprint=p.FootprintLoad(str(out/'Handset.pretty'),'ECS_TXO_32CSMV_3225')
 expected={'1':(-1.1,.8),'2':(1.1,.8),'3':(1.1,-.8),'4':(-1.1,-.8)}
 if {q.GetNumber() for q in footprint.Pads()}!=set(expected):errors.append('TCXO land count')
 for q in footprint.Pads():
  pos=(round(p.ToMM(q.GetPosition().x),3),round(p.ToMM(q.GetPosition().y),3))
  size=(round(p.ToMM(q.GetSize().x),3),round(p.ToMM(q.GetSize().y),3))
  if pos!=expected.get(q.GetNumber()) or size!=(1.4,1.2):errors.append('TCXO land '+q.GetNumber())
 sheet=parse((out/'radios.kicad_sch').read_text());symbols=children(child(sheet,'lib_symbols'),'symbol')
 radio=next(s for s in symbols if s[1]=='Handset:SX1262_TCXO_DIO3Supply')
 pins={child(pin,'number')[1]:pin for unit in children(radio,'symbol') for pin in children(unit,'pin')}
 if pins['6'][1]!='power_out':errors.append('DIO3 supply function symbol')
 board=check_board(p.LoadBoard(str(out/'handset.kicad_pcb')))
 return dict(passed=not errors and board['passed'] and all(c['rejected'] for c in negative),
  circuit_failures=errors,negative_tests=negative,copper=board,
  qualification_open=['TCXO maximum output amplitude is not specified in series data; confirm <=1.2Vpp with supplier/bench evidence.',
   'Verify DIO3 ramp/current, oscillator startup, loaded frequency, temperature drift and phase noise.',
   'Qualify routed SX1262 supply/ground; complete thermal layout, RF frontend and conducted/antenna qualification.'],fabrication_released=False)

if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
 report=inspect(out);(out/'sx1262-clock-checks.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2));sys.exit(not report['passed'])
