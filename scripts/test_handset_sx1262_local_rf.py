#!/usr/bin/env python3
"""Copper open-pad and layer/reference regression controls for local PA/RF."""
import json,subprocess,sys,unittest
from pathlib import Path
import pcbnew as p
from check_handset_sx1262_local_rf import check_board,ROOT
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
class LocalRFTests(unittest.TestCase):
 def board(self):return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
 def test_installed(self):self.assertTrue(check_board(self.board())['passed'])
 def isolate(self,ref,pin):
  b=self.board();f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
  q=next(q for q in f.Pads() if q.GetNumber()==pin);q.SetPosition(p.VECTOR2I(p.FromMM(200),p.FromMM(200)))
  self.assertFalse(check_board(b)['passed'])
 def test_pa_feed_open(self):self.isolate('U4','24')
 def test_choke_open(self):self.isolate('L13','2')
 def test_bypass_ground_open(self):self.isolate('C101','2')
 def test_tx_open(self):self.isolate('U36','1')
 def test_rx_n_open(self):self.isolate('U36','3')
 def test_rx_p_open(self):self.isolate('U36','4')
 def test_wrong_rf_layer(self):
  b=self.board()
  for t in b.GetTracks():
   if t.GetNetname()=='SX_RFO':t.SetLayer(p.F_Cu)
  self.assertFalse(check_board(b)['passed'])
 def test_missing_reference(self):
  b=self.board()
  for zone in b.Zones():
   if zone.GetZoneName()=='SX1262 clock return' and zone.GetLayer()==p.In2_Cu:zone.Move(p.VECTOR2I(p.FromMM(100),p.FromMM(100)))
  r=check_board(b);self.assertFalse(r['passed']);self.assertTrue(r['reference_gaps'])
if __name__=='__main__':
 if '--case' in sys.argv:
  name=sys.argv[sys.argv.index('--case')+1]
  result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([LocalRFTests(name)]));sys.exit(not result.wasSuccessful())
 cases=unittest.defaultTestLoader.getTestCaseNames(LocalRFTests);failed=[]
 for name in cases:
  r=subprocess.run([sys.executable,__file__,str(OUT),'--case',name],capture_output=True,text=True)
  print(name+(': PASS' if r.returncode==0 else ': FAIL'))
  if r.returncode:failed.append(name);print(r.stdout);print(r.stderr)
 (OUT/'sx1262-local-rf-tests.json').write_text(json.dumps(dict(tests=len(cases),failed_cases=failed,passed=not failed,fabrication_released=False),indent=2)+'\n');sys.exit(bool(failed))
