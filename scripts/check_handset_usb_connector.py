#!/usr/bin/env python3
"""Independently check USB4105 land relief, locating holes and retained solder area."""
import json,math,sys
from pathlib import Path
import pcbnew as p
p.SwigPyIterator.next=p.SwigPyIterator.__next__
ROOT=Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/generated'
def inspect(b):
 f=next(f for f in b.GetFootprints() if f.GetReference()=='USB1');checks=[];clearances={}
 def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
 check('USB4105 retained',f.GetValue()=='USB4105')
 check('custom footprint selected',str(f.GetFPID().GetLibItemName())=='USB4105_GroundCornerRelief')
 check('placement unchanged',abs(p.ToMM(f.GetPosition().x)-130)<1e-6 and abs(p.ToMM(f.GetPosition().y)-56)<1e-6 and abs(f.GetOrientationDegrees()-90)<1e-6)
 holes=[q for q in f.Pads() if q.GetAttribute()==p.PAD_ATTRIB_NPTH]
 check('two 0.65 mm locating holes',len(holes)==2 and all(q.GetDrillSize()==p.VECTOR2I(p.FromMM(.65),p.FromMM(.65)) for q in holes))
 check('locating holes stay at drawing coordinates',sorted((round(p.ToMM(q.GetPosition().x),3),round(p.ToMM(q.GetPosition().y),3)) for q in holes)==[(127.395,53.11),(127.395,58.89)])
 expected={'A1':-3.2,'B12':-3.2,'A12':3.2,'B1':3.2}
 check('all four named ground pads present',sorted(q.GetNumber() for q in f.Pads() if q.GetNumber() in expected)==sorted(expected))
 for q in f.Pads():
  pin=q.GetNumber()
  if pin not in expected:continue
  check(pin+' ground',q.GetNetname()=='GND')
  check(pin+' unchanged envelope',q.GetSize()==p.VECTOR2I(p.FromMM(.6),p.FromMM(1.15)))
  check(pin+' unchanged position',abs(p.ToMM(q.GetPosition().x)-126.32)<1e-6 and abs(p.ToMM(q.GetPosition().y)-(56-expected[pin]))<1e-6)
  poly=q.GetEffectivePolygon(p.F_Cu,p.ERROR_OUTSIDE)
  clearance=min(p.ToMM(poly.Distance(h.GetPosition()))-p.ToMM(h.GetDrillSize().x)/2 for h in holes) if holes else -1
  clearances[pin]=round(clearance,6);check(pin+' hole clearance >= 0.25 mm',clearance>=.25)
  # Engineering retention criterion, not an assertion of assembler approval:
  # a continuous 0.45 x 0.75 mm central solder rectangle remains in each land.
  a=math.radians(q.GetOrientationDegrees());inside=q.GetEffectivePolygon(p.F_Cu,p.ERROR_INSIDE)
  for x,y in [(-.225,-.475),(.225,-.475),(.225,.275),(-.225,.275)]:
   point=p.VECTOR2I(q.GetPosition().x+p.FromMM(x*math.cos(a)+y*math.sin(a)),q.GetPosition().y+p.FromMM(-x*math.sin(a)+y*math.cos(a)))
   check(pin+' retained solder core '+str((x,y)),inside.Contains(point))
 return dict(passed=all(c['passed'] for c in checks),checks=checks,ground_to_hole_clearance_mm=clearances,retained_solder_core_mm=[.45,.75],scope='Nominal CAD geometry; modified contour requires assembler DFM/solder-joint review',fabrication_released=False)
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT;r=inspect(p.LoadBoard(str(out/'handset.kicad_pcb')));(out/'usb-connector-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
