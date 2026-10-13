#!/usr/bin/env python3
"""Negative controls for radio-host continuity and new digital copper."""
import json,sys
from pathlib import Path
import pcbnew as p
from check_handset_sx1262_digital import ROOT,GROUPS,check_board
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
manifest=json.loads((OUT/'sx1262-digital-routing.json').read_text());cases=[]
def load():return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
def test(name,ok):cases.append(dict(test=name,passed=bool(ok)))
test('installed digital copper',check_board(load(),manifest)['passed'])
for key in ['U4.13','U4.14','U4.15','U4.16','U4.17','U4.18','U4.19','U1.9','U1.10','U1.11','U1.23','R10.1','R10.2']:
 b=load();ref,pin=key.split('.')
 q=next(q for f in b.GetFootprints() if f.GetReference()==ref for q in f.Pads() if q.GetNumber()==pin);q.Move(p.VECTOR2I(p.FromMM(100),0));test('disconnect '+key,not check_board(b,manifest)['passed'])
b=load();next(f for f in b.GetFootprints() if f.GetReference()=='R10').SetValue('100k');test('wrong pull-up value',not check_board(b,manifest)['passed'])
b=load();t=next(t for t in b.GetTracks() if t.m_Uuid.AsString() in manifest['added_copper_uuids'] and t.GetClass()=='PCB_TRACK');t.SetWidth(p.FromMM(.1));test('unreviewed trace width',not check_board(b,manifest)['passed'])
b=load();v=next(t for t in b.GetTracks() if t.m_Uuid.AsString() in manifest['added_copper_uuids'] and t.GetClass()=='PCB_VIA');v.SetBackTentingMode(p.TENTING_MODE_NOT_TENTED);test('via tenting removed',not check_board(b,manifest)['passed'])
r=dict(passed=all(c['passed'] for c in cases),tests=len(cases),cases=cases,fabrication_released=False);(OUT/'sx1262-digital-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
