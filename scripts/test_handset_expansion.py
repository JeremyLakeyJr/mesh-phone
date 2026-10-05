#!/usr/bin/env python3
"""Reject expansion topology changes and physically severed control/signal copper."""
import copy,json,sys,unittest
from pathlib import Path
import pcbnew as p
from check_handset_expansion import ROOT,check_board,check_circuit
from handset_expansion_contract import validate
from cad_sexpr import parse,dump,child
OUT=Path(sys.argv.pop()) if len(sys.argv)>1 and not sys.argv[-1].startswith('-') else ROOT
class ExpansionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.spec,cls.values,cls.nets,cls.fields=check_circuit(OUT)
 def test_contract(self):validate(self.spec,self.values,self.nets,self.fields)
 def test_unsafe_topology_rejected(self):
  for ref,pin,net in [('U14','3','+3V3'),('U33','6','+3V3'),('U35','13','+3V3'),('U34','19','GND'),('R20','1','I2C_SCL'),('U34','18','EXP_SW_SDA'),('R83','2','+3V3')]:
   with self.subTest(ref=ref,pin=pin):
    spec=copy.deepcopy(self.spec);nets=self.nets.copy();spec[ref]['nets'][pin]=nets[ref,pin]=net
    with self.assertRaises(ValueError):validate(spec,self.values,nets,self.fields)
 def test_wrong_parts_rejected(self):
  for ref,mpn in [('U33','TCA9536'),('U35','SN74HC10'),('R86','RC0402FR-0710KL')]:
   spec=copy.deepcopy(self.spec);fields=copy.deepcopy(self.fields);spec[ref]['mpn']=fields[ref]['MPN']=mpn
   with self.assertRaises(ValueError):validate(spec,self.values,self.nets,fields)
 def test_strap_and_psram_pins_remain_unused(self):
  for pin in ['16','26','28','29','30']:
   spec=copy.deepcopy(self.spec);spec['U1']['nets'][pin]='EXP_PWR_EN'
   with self.assertRaises(ValueError):validate(spec,self.values,self.nets,self.fields)
 def test_actual_copper(self):self.assertTrue(check_board(p.LoadBoard(str(OUT/'handset.kicad_pcb')))['passed'])
 def test_severed_control_and_signal_detected(self):
  for net in ['EXP_PWR_EN','EXP_IO_OE_N','EXP_SW_MOSI','MCU_EN']:
   with self.subTest(net=net):
    tree=parse((OUT/'handset.kicad_pcb').read_text())
    tree[:]=[n for n in tree if not(isinstance(n,list) and n[0] in ('segment','via') and str(child(n,'net')[1])==net)]
    path=Path('/tmp/expansion-cut.kicad_pcb');path.write_text(dump(tree)+'\n')
    report=check_board(p.LoadBoard(str(path)))
    self.assertFalse(next(g for g in report['groups'] if g['net']==net)['passed'])
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExpansionTests))
 (OUT/'expansion-negative-tests.json').write_text(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful()),indent=2)+'\n')
 sys.exit(0 if result.wasSuccessful() else 1)
