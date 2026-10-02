#!/usr/bin/env python3
"""Ensure missing display copper and incorrect output-enable wiring fail closed."""
import copy,tempfile,unittest,json
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,dump,child,children,prop,Q
from check_handset_display_routing import ROOT,check_board

class DisplayRoutingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tree=parse((ROOT/'handset.kicad_pcb').read_text())

 def report(self,tree):
  with tempfile.TemporaryDirectory(prefix='display-negative-') as d:
   path=Path(d)/'handset.kicad_pcb';path.write_text(dump(tree)+'\n')
   return check_board(p.LoadBoard(str(path)))

 def test_installed_board_passes(self):
  self.assertTrue(self.report(self.tree)['passed'])

 def test_cut_display_supply_detected(self):
  tree=copy.deepcopy(self.tree)
  tree[:]=[n for n in tree if not (isinstance(n,list) and n[0] in ('segment','via') and child(n,'net') and child(n,'net')[1]=='LCD_3V0')]
  report=self.report(tree)
  self.assertFalse(report['passed'])
  self.assertTrue(next(g for g in report['groups'] if g['net']=='LCD_3V0')['disconnected'])

 def test_cut_clock_detected(self):
  tree=copy.deepcopy(self.tree)
  tree[:]=[n for n in tree if not (isinstance(n,list) and n[0] in ('segment','via') and child(n,'net') and child(n,'net')[1]=='PANEL_SPI_SCK')]
  report=self.report(tree)
  self.assertFalse(report['passed'])
  self.assertTrue(next(g for g in report['groups'] if g['net']=='PANEL_SPI_SCK')['disconnected'])

 def test_missing_ground_extension_rejected(self):
  tree=copy.deepcopy(self.tree)
  zone=next(z for z in children(tree,'zone') if child(z,'name') and child(z,'name')[1]=='Display interface ground extension')
  tree.remove(zone)
  report=self.report(tree)
  self.assertFalse(report['passed'])
  self.assertTrue(next(g for g in report['groups'] if g['net']=='GND')['disconnected'])

 def test_miso_always_enabled_rejected(self):
  tree=copy.deepcopy(self.tree)
  fp=next(f for f in children(tree,'footprint') if prop(f,'Reference')[2]=='U30')
  pad=next(q for q in children(fp,'pad') if q[1]=='1')
  child(pad,'net')[1]=Q('GND')
  report=self.report(tree)
  self.assertFalse(report['passed'])
  self.assertIn('U30.1',report['pin_contract_failures'])

if __name__=='__main__':
 result=unittest.main(exit=False).result
 (ROOT/'display-routing-negative-tests.json').write_text(json.dumps(dict(tests_run=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors)),indent=2)+'\n')
 raise SystemExit(not result.wasSuccessful())
