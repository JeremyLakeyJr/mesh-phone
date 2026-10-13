#!/usr/bin/env python3
"""Negative controls for radio-host continuity and new digital copper."""
import json,sys
from pathlib import Path
import pcbnew as p
from check_handset_cc1101_digital import ROOT,GROUPS,check_board
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
manifest=json.loads((OUT/'cc1101-digital-routing.json').read_text());cases=[]
def load():return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
def test(name,ok):cases.append(dict(test=name,passed=bool(ok)))
test('installed digital copper',check_board(load(),manifest)['passed'])
for key in ['U5.1','U5.2','U5.3','U5.6','U5.7','U5.20','U1.24','U1.25','R12.1','R12.2','TP1.1']:
 b=load();ref,pin=key.split('.')
 q=next(q for f in b.GetFootprints() if f.GetReference()==ref for q in f.Pads() if q.GetNumber()==pin);q.Move(p.VECTOR2I(p.FromMM(100),0));test('disconnect '+key,not check_board(b,manifest)['passed'])
b=load();next(f for f in b.GetFootprints() if f.GetReference()=='R12').SetValue('100k');test('wrong pull-up value',not check_board(b,manifest)['passed'])
b=load();t=next(t for t in b.GetTracks() if t.m_Uuid.AsString() in manifest['added_copper_uuids'] and t.GetClass()=='PCB_TRACK');t.SetWidth(p.FromMM(.1));test('unreviewed trace width',not check_board(b,manifest)['passed'])
b=load();v=next(t for t in b.GetTracks() if t.m_Uuid.AsString() in manifest['added_copper_uuids'] and t.GetClass()=='PCB_VIA');v.SetBackTentingMode(p.TENTING_MODE_NOT_TENTED);test('via tenting removed',not check_board(b,manifest)['passed'])
r=dict(passed=all(c['passed'] for c in cases),tests=len(cases),cases=cases,fabrication_released=False);(OUT/'cc1101-digital-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
