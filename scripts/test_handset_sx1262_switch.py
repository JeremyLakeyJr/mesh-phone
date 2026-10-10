#!/usr/bin/env python3
"""Negative controls for switched RF copper and reference checks."""
import json,sys
from pathlib import Path
import pcbnew as p
from check_handset_sx1262_switch import check_board,ROOT
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT

def run():
 cases=[]
 def load():return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
 def test(name,passed):cases.append(dict(test=name,passed=bool(passed)));print(name,':',bool(passed),flush=True)
 test('installed switched RF layout',check_board(load())['passed'])
 for key in ['U36.8','U36.6','C99.2','C100.2','U37.5','C98.2','U37.6','U37.4','U37.2','R92.1','J20.1','J20.2']:
  b=load();ref,pin=key.split('.')
  q=next(q for f in b.GetFootprints() if f.GetReference()==ref for q in f.Pads() if q.GetNumber()==pin)
  q.SetPosition(p.VECTOR2I(p.FromMM(200),p.FromMM(200)))
  r=check_board(b);test('isolate '+key,any('full pad continuity' in c['check'] and not c['passed'] for c in r['checks']))
 b=load();v=next(t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='SX_RX_MATCH')
 v.SetBackTentingMode(p.TENTING_MODE_NOT_TENTED);test('RF via tenting removed',not check_board(b)['passed'])
 b=load()
 for z in b.Zones():
  if z.GetNetname()=='GND' and (z.IsOnLayer(p.In1_Cu) or z.IsOnLayer(p.In2_Cu)):z.Move(p.VECTOR2I(p.FromMM(100),0))
 r=check_board(b);test('RF reference planes moved away',bool(r['reference_gaps']))
 b=load()
 for t in b.GetTracks():
  if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND':t.SetPosition(p.VECTOR2I(p.FromMM(200),p.FromMM(200)))
 r=check_board(b);test('transition return vias removed',any('close connected transition return' in c['check'] and not c['passed'] for c in r['checks']))
 b=load();t=next(t for t in b.GetTracks() if t.GetClass()=='PCB_TRACK' and t.GetNetname()=='SX_ANT_AC');t.SetWidth(p.FromMM(.1));r=check_board(b)
 test('unreviewed RF trace width',any('reviewed width range' in c['check'] and not c['passed'] for c in r['checks']))
 report=dict(tests=len(cases),cases=cases,passed=all(c['passed'] for c in cases),fabrication_released=False)
 (OUT/'sx1262-switch-tests.json').write_text(json.dumps(report,indent=2)+'\n');return report['passed']
if __name__=='__main__':sys.exit(not run())
