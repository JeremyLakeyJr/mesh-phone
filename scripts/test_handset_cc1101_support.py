#!/usr/bin/env python3
"""Negative controls for CC1101 continuity, bypass islands and mask coverage."""
import json,sys
from pathlib import Path
import pcbnew as p
from check_handset_cc1101_support import ROOT,check_board
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
cases=[]
def load():return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
def test(name,ok):cases.append(dict(test=name,passed=bool(ok)))
def pad(b,key):
 ref,pin=key.split('.');return next(q for f in b.GetFootprints() if f.GetReference()==ref for q in f.Pads() if q.GetNumber()==pin)
def point(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
test('installed layout',check_board(load())['passed'])
for key in ['U5.8','Y2.3','C61.1','C11.1','R11.1','L11.1','L11.2','C74.1','C12.1','C69.1','C70.1','C71.1','C72.1','C73.1','C62.2']:
 b=load();pad(b,key).SetPosition(point(200,200));test('disconnect '+key,not check_board(b)['passed'])
b=load();ep=pad(b,'U5.21');layers=ep.GetLayerSet();layers.AddLayer(p.B_Mask);ep.SetLayerSet(layers);test('exposed thermal holes',not check_board(b)['passed'])
b=load();v=next(t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetPosition()==point(121.5,39));v.SetBackTentingMode(p.TENTING_MODE_NOT_TENTED);test('thermal tenting removed',not check_board(b)['passed'])
b=load();v=next(t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetPosition()==point(121.5,39));v.SetPosition(point(122.3,39.8));test('thermal drill in mask window',not check_board(b)['passed'])
b=load();t=next(t for t in b.GetTracks() if t.GetNetname()=='CC_X1');t.SetLayer(p.F_Cu);test('oscillator wrong layer',not check_board(b)['passed'])
b=load()
for z in b.Zones():
 if z.GetNetname()=='GND' and z.IsOnLayer(p.In2_Cu):z.Move(point(100,0))
test('oscillator ground removed',not check_board(b)['passed'])
b=load();t=p.PCB_TRACK(b);t.SetStart(pad(b,'U5.14').GetPosition());t.SetEnd(pad(b,'U5.15').GetPosition());t.SetWidth(p.FromMM(.2));t.SetLayer(p.B_Cu);t.SetNet(b.FindNet('CC_VDD'));b.Add(t);test('adjacent supplies bypass capacitors',not check_board(b)['passed'])
r=dict(passed=all(c['passed'] for c in cases),tests=len(cases),cases=cases,fabrication_released=False);(OUT/'cc1101-support-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(not r['passed'])
