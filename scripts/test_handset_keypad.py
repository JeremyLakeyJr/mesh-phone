#!/usr/bin/env python3
"""Isolated negative controls for the core routing contract."""
import json, subprocess, sys, unittest
from pathlib import Path
import pcbnew as p
from check_handset_keypad import check_board, ROOT
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
class KeypadTests(unittest.TestCase):
 def board(self):return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
 def test_installed(self):self.assertTrue(check_board(self.board())['passed'])
 def isolate(self,ref,pin):
  b=self.board();f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
  q=next(q for q in f.Pads() if q.GetNumber()==pin);q.SetPosition(p.VECTOR2I(p.FromMM(200),p.FromMM(200)))
  self.assertFalse(check_board(b)['passed'])
 def test_open_row(self):self.isolate('U2','8')
 def test_open_column(self):self.isolate('U2','12')
 def test_single_duplicate_contact(self):self.isolate('SW10','1')
 def test_swapped_rows(self):
  b=self.board();f=next(f for f in b.GetFootprints() if f.GetReference()=='U2')
  for q in f.Pads():
   if q.GetNumber()=='8':q.SetNet(b.FindNet('KEY_ROW1'))
   if q.GetNumber()=='7':q.SetNet(b.FindNet('KEY_ROW0'))
  self.assertFalse(check_board(b)['passed'])
if __name__=='__main__':
 if '--case' in sys.argv:
  name=sys.argv[sys.argv.index('--case')+1]
  result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([KeypadTests(name)]));sys.exit(not result.wasSuccessful())
 cases=unittest.defaultTestLoader.getTestCaseNames(KeypadTests);failed=[]
 for name in cases:
  result=subprocess.run([sys.executable,__file__,str(OUT),'--case',name],capture_output=True,text=True)
  print(name+(': PASS' if result.returncode==0 else ': FAIL'))
  if result.returncode:failed.append(name);print(result.stdout);print(result.stderr)
 (OUT/'keypad-routing-tests.json').write_text(json.dumps(dict(tests=len(cases),failed_cases=failed,passed=not failed,fabrication_released=False),indent=2)+'\n');sys.exit(bool(failed))
