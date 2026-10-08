#!/usr/bin/env python3
"""Isolated open-pad controls for SX1262 supply and ground continuity."""
import json, subprocess, sys, unittest
from pathlib import Path
import pcbnew as p
from check_handset_sx1262_supply import check_board, ROOT
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
class SupplyTests(unittest.TestCase):
 def board(self):return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
 def test_installed(self):self.assertTrue(check_board(self.board())['passed'])
 def isolate(self,ref,pin):
  b=self.board();f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
  q=next(q for q in f.Pads() if q.GetNumber()==pin);q.SetPosition(p.VECTOR2I(p.FromMM(200),p.FromMM(200)))
  self.assertFalse(check_board(b)['passed'])
 def test_open_vdd(self):self.isolate('U4','1')
 def test_open_vbat(self):self.isolate('U4','10')
 def test_open_io(self):self.isolate('U4','11')
 def test_open_bypass(self):self.isolate('C75','1')
 def test_open_bypass_ground(self):self.isolate('C8','2')
 def test_open_ground(self):self.isolate('U4','20')
if __name__=='__main__':
 if '--case' in sys.argv:
  name=sys.argv[sys.argv.index('--case')+1]
  result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([SupplyTests(name)]));sys.exit(not result.wasSuccessful())
 cases=unittest.defaultTestLoader.getTestCaseNames(SupplyTests);failed=[]
 for name in cases:
  result=subprocess.run([sys.executable,__file__,str(OUT),'--case',name],capture_output=True,text=True)
  print(name+(': PASS' if result.returncode==0 else ': FAIL'))
  if result.returncode:failed.append(name);print(result.stdout);print(result.stderr)
 (OUT/'sx1262-supply-tests.json').write_text(json.dumps(dict(tests=len(cases),failed_cases=failed,passed=not failed,fabrication_released=False),indent=2)+'\n');sys.exit(bool(failed))
