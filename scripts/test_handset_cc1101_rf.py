#!/usr/bin/env python3
"""Negative controls for CC1101 RF copper and reference checks."""
import json,sys
from pathlib import Path
import pcbnew as p
from check_handset_cc1101_rf import ROOT,GROUPS,check_board
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
cases=[]
def load():return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
def test(name,ok):cases.append(dict(test=name,passed=bool(ok)))
test('installed RF copper',check_board(load())['passed'])
for key in sorted(set(' '.join(GROUPS.values()).split())-{'U1.1'}):
 b=load();ref,pin=key.split('.')
 for f in b.GetFootprints():
  if f.GetReference()==ref:
   for q in f.Pads():
    if q.GetNumber()==pin:q.Move(p.VECTOR2I(p.FromMM(100),0))
 test('disconnect '+key,not check_board(b)['passed'])
b=load()
for z in b.Zones():
 if z.GetNetname()=='GND' and z.IsOnLayer(p.In2_Cu):z.Move(p.VECTOR2I(p.FromMM(100),0))
test('RF reference removed',not check_board(b)['passed'])
b=load();t=next(t for t in b.GetTracks() if t.GetNetname()=='CC_RF_50R');t.SetWidth(p.FromMM(.1));test('antenna width changed',not check_board(b)['passed'])
b=load();t=next(t for t in b.GetTracks() if t.GetNetname()=='CC_RF_P');t.SetLayer(p.F_Cu);test('RF wrong layer',not check_board(b)['passed'])
r=dict(passed=all(c['passed'] for c in cases),tests=len(cases),cases=cases,fabrication_released=False);(OUT/'cc1101-rf-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
