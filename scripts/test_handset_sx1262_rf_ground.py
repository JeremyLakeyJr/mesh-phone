#!/usr/bin/env python3
"""Regression controls for RF grounds and native scoped drill-rule enforcement."""
import json,shutil,subprocess,sys,tempfile
from pathlib import Path
import pcbnew as p
from check_handset_sx1262_rf_ground import inspect,check_board,check_rules,ROOT
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT

def run():
 tests=[]
 def test(name,result):tests.append(dict(test=name,passed=bool(result)));print(name,':',bool(result),flush=True)
 test('installed board and rules',inspect(OUT)['passed'])
 for pin in ['2','5','7','9','10']:
  b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));f=next(f for f in b.GetFootprints() if f.GetReference()=='U36')
  q=next(q for q in f.Pads() if q.GetNumber()==pin);q.SetPosition(p.VECTOR2I(p.FromMM(200),p.FromMM(200)))
  test('isolated U36 ground '+pin,not check_board(b)['passed'])
 b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));v=next(t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetDrillValue()==p.FromMM(.2))
 v.SetBackTentingMode(p.TENTING_MODE_NOT_TENTED);test('missing back tenting',not check_board(b)['passed'])
 b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));f=next(f for f in b.GetFootprints() if f.GetReference()=='U36')
 q=next(q for q in f.Pads() if q.GetNumber()=='10')
 v=min((t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetDrillValue()==p.FromMM(.2)),key=lambda t:(t.GetPosition()-q.GetPosition()).EuclideanNorm())
 v.SetPosition(q.GetPosition());r=check_board(b)
 test('drill overlapping a land rejected',any('nominal land gap' in c['check'] and not c['passed'] for c in r['checks']))
 with tempfile.TemporaryDirectory(prefix='sx-rf-drill-tests-') as temp:
  base=Path(temp)
  for case,pos,net,drill,diameter,wanted in [
   ('small via outside RF area',(120,56),'GND',.2,.45,'General'),
   ('small signal via inside RF area',(114.8,41.1),'SX_RF_SW',.2,.45,'General'),
   ('wrong RF ground drill',(114.8,41.1),'GND',.3,.45,'SX1262 RF ground vias')]:
   b=p.LoadBoard(str(OUT/'handset.kicad_pcb'));v=p.PCB_VIA(b);v.SetPosition(p.VECTOR2I(p.FromMM(pos[0]),p.FromMM(pos[1])));v.SetWidth(p.FromMM(diameter));v.SetDrill(p.FromMM(drill));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));b.Add(v)
   if net!='GND':
    # A pad anchors the signal net; a floating via touching cached ground fill
    # can otherwise be reassigned to GND by KiCad's connectivity propagation.
    f=p.FOOTPRINT(b);f.SetReference('RF_RULE_TEST');b.Add(f)
    q=p.PAD(f);q.SetNumber('1');q.SetAttribute(p.PAD_ATTRIB_SMD);q.SetShape(p.PAD_SHAPE_CIRCLE)
    q.SetSize(p.VECTOR2I(p.FromMM(.1),p.FromMM(.1)));layers=p.LSET();layers.AddLayer(p.F_Cu);q.SetLayerSet(layers)
    q.SetPosition(v.GetPosition());q.SetNet(b.FindNet(net));f.Add(q)
   ident=v.m_Uuid.AsString();p.SaveBoard(str(base/'handset.kicad_pcb'),b)
   for name in ['handset.kicad_pro','handset.kicad_dru']:shutil.copy2(OUT/name,base/name)
   r=subprocess.run(['kicad-cli','pcb','drc',str(base/'handset.kicad_pcb'),'--format','json','-o',str(base/'drc.json')],capture_output=True,text=True)
   if r.returncode:raise RuntimeError(r.stdout+r.stderr)
   findings=json.loads((base/'drc.json').read_text())['violations']
   rejected=[x for x in findings if wanted in x['description'] and any(i['uuid']==ident for i in x['items']) and x['type'] in ('drill_out_of_range','via_diameter')]
   test(case+' rejected by native size rule',bool(rejected))
   if not rejected:print(json.dumps(findings,indent=2))
  (base/'handset.kicad_dru').unlink();test('missing custom rules fails closed',bool(check_rules(base)))
  text=(OUT/'handset.kicad_dru').read_text().replace('(min 0.3mm)','(min 0.2mm)')
  (base/'handset.kicad_dru').write_text(text);test('weakened general drill rule rejected',bool(check_rules(base)))
 report=dict(tests=len(tests),cases=tests,passed=all(t['passed'] for t in tests),fabrication_released=False)
 (OUT/'sx1262-rf-ground-tests.json').write_text(json.dumps(report,indent=2)+'\n');return report['passed']
if __name__=='__main__':sys.exit(not run())
