#!/usr/bin/env python3
"""Isolated negative controls for the core routing contract."""
import json, subprocess, sys, unittest
from pathlib import Path
import pcbnew as p
from check_handset_core import check_board, ROOT
p.SwigPyIterator.next=p.SwigPyIterator.__next__
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT
class CoreTests(unittest.TestCase):
 def board(self): return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
 def test_installed(self): self.assertTrue(check_board(self.board())['passed'])
 def isolate(self,ref,pin,expected):
  b=self.board();f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
  q=next(q for q in f.Pads() if q.GetNumber()==pin)
  # Move one physical pad only: duplicate switch pins must each be checked.
  q.SetPosition(p.VECTOR2I(p.FromMM(200),p.FromMM(200)))
  report=check_board(b)
  self.assertFalse(report['passed'])
  self.assertTrue(any(c['check']==expected and not c['passed'] for c in report['checks']))
 def test_open_boot_pullup(self): self.isolate('R2','1','+3V3')
 def test_open_boot_contact(self): self.isolate('SW17','1','MCU_BOOT')
 def test_open_reset_contact(self): self.isolate('SW18','1','MCU_EN')
 def test_open_controller_power(self): self.isolate('U2','21','+3V3')
 def test_open_controller_reset(self): self.isolate('U2','20','MCU_EN')
 def test_wrong_pullup(self):
  b=self.board();next(f for f in b.GetFootprints() if f.GetReference()=='R2').SetValue('100')
  self.assertFalse(check_board(b)['passed'])
 def test_swapped_bus(self):
  b=self.board();f=next(f for f in b.GetFootprints() if f.GetReference()=='U2')
  for q in f.Pads():
   if q.GetNumber()=='22': q.SetNet(b.FindNet('I2C_SCL'))
   if q.GetNumber()=='23': q.SetNet(b.FindNet('I2C_SDA'))
  self.assertFalse(check_board(b)['passed'])
if __name__=='__main__':
 if '--case' in sys.argv:
  name=sys.argv[sys.argv.index('--case')+1]
  result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([CoreTests(name)]));sys.exit(not result.wasSuccessful())
 cases=unittest.defaultTestLoader.getTestCaseNames(CoreTests);failed=[]
 for name in cases:
  result=subprocess.run([sys.executable,__file__,str(OUT),'--case',name],capture_output=True,text=True)
  print(name+(': PASS' if result.returncode==0 else ': FAIL'))
  if result.returncode:failed.append(name);print(result.stdout);print(result.stderr)
 (OUT/'core-routing-tests.json').write_text(json.dumps(dict(tests=len(cases),failed_cases=failed,passed=not failed,fabrication_released=False),indent=2)+'\n');sys.exit(bool(failed))
