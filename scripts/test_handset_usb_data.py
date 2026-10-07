#!/usr/bin/env python3
"""Negative controls for the saved USB routing checks, never mutate the saved PCB."""
import json,sys,unittest,subprocess
from pathlib import Path
import pcbnew as p
from check_handset_usb_data import inspect,ROOT
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
class USBDataTests(unittest.TestCase):
 def board(self):return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
 def test_installed_routing(self):self.assertTrue(inspect(self.board())['passed'])
 def test_removed_esd_pass_through(self):
  b=self.board()
  track=next(t for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetNetname()=='USB_D_N' and abs(p.ToMM(t.GetStart().x)-120.615)<1e-5 and abs(p.ToMM(t.GetEnd().x)-121.385)<1e-5)
  b.Remove(track);r=inspect(b);self.assertFalse(r['passed']);self.assertTrue(any(not c['passed'] and 'continuity' in c['check'] for c in r['checks']))
 def test_swapped_host_polarity(self):
  b=self.board();f=next(f for f in b.GetFootprints() if f.GetReference()=='U1')
  for q in f.Pads():
   if q.GetNumber()=='13':q.SetNet(b.FindNet('USB_HOST_D_P'))
   if q.GetNumber()=='14':q.SetNet(b.FindNet('USB_HOST_D_N'))
  r=inspect(b);self.assertFalse(r['passed']);self.assertTrue(any(not c['passed'] and 'pin assignment' in c['check'] for c in r['checks']))
 def test_missing_reference_fill(self):
  b=self.board()
  for z in b.Zones():
   if z.IsOnLayer(p.In2_Cu):z.UnFill()
  r=inspect(b);self.assertFalse(r['passed']);self.assertTrue(r['reference_gaps'])
 def test_missing_transition_return(self):
  b=self.board();v=next(t for t in b.GetTracks() if isinstance(t,p.PCB_VIA) and abs(p.ToMM(t.GetPosition().x)-106.5)<1e-5 and abs(p.ToMM(t.GetPosition().y)-49.1)<1e-5);b.Remove(v)
  r=inspect(b);self.assertFalse(r['passed']);self.assertTrue(any(not c['passed'] and 'ground return via' in c['check'] for c in r['checks']))
 def test_wrong_termination(self):
  b=self.board();next(f for f in b.GetFootprints() if f.GetReference()=='R88').SetValue('0')
  self.assertFalse(inspect(b)['passed'])
 def test_added_length_mismatch(self):
  b=self.board();count=0
  for t in b.GetTracks():
   if isinstance(t,p.PCB_VIA) or t.GetNetname()!='USB_HOST_D_P':continue
   for getter,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
    pos=getter()
    if abs(p.ToMM(pos.x)-94.25)<1e-5 and abs(p.ToMM(pos.y)-49.435076)<1e-5:setter(p.VECTOR2I(pos.x,p.FromMM(49.8)));count+=1
  self.assertEqual(count,2);r=inspect(b)
  self.assertTrue(all(c['passed'] for c in r['checks'] if 'physical continuity' in c['check']))
  self.assertTrue(any(not c['passed'] for c in r['checks'] if 'planar skew' in c['check']))
if __name__=='__main__':
 # Isolate KiCad's native/SWIG lifetime for destructive in-memory negative controls.
 if '--case' in sys.argv:
  name=sys.argv[sys.argv.index('--case')+1];result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([USBDataTests(name)]));sys.exit(not result.wasSuccessful())
 cases=unittest.defaultTestLoader.getTestCaseNames(USBDataTests);failed=[]
 for name in cases:
  result=subprocess.run([sys.executable,__file__,str(OUT),'--case',name],capture_output=True,text=True)
  print(name+(': PASS' if result.returncode==0 else ': FAIL'))
  if result.returncode:failed.append(name);print(result.stdout);print(result.stderr)
 (OUT/'usb-data-tests.json').write_text(json.dumps(dict(tests=len(cases),failed_cases=failed,passed=not failed,fabrication_released=False),indent=2)+'\n');sys.exit(bool(failed))
