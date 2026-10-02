#!/usr/bin/env python3
"""Negative tests for backlight topology, population and actual copper."""
import copy,json,sys,unittest
from pathlib import Path
import xml.etree.ElementTree as ET
import pcbnew as p
from handset_backlight_contract import validate,screening
from check_handset_backlight_routing import check_board,ROOT
from cad_sexpr import parse,dump,child,children,prop
OUT=Path(sys.argv.pop()) if len(sys.argv)>1 and not sys.argv[-1].startswith('-') else ROOT
class BacklightTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.spec={c['ref']:c for c in json.loads((OUT/'connectivity.json').read_text())}
  xml=ET.parse(OUT/'netlist.xml').getroot()
  cls.values={c.attrib['ref']:c.findtext('value') for c in xml.findall('./components/comp')}
  cls.nets={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')}
  cls.fields={c.attrib['ref']:{f.attrib['name']:f.text for f in c.findall('./fields/field')} for c in xml.findall('./components/comp')}
 def test_installed_contract(self):validate(self.spec,self.values,self.nets,self.fields)
 def test_channel_and_default_off_mutations(self):
  for ref,pin,wrong in [('U32','3','LCD_K2'),('U32','9','LCD_BL_GATE'),('R57','2','+3V3'),('R82','2','LCD_K1'),('U2','14','GND')]:
   with self.subTest(ref=ref,pin=pin):
    spec=copy.deepcopy(self.spec);nets=self.nets.copy();spec[ref]['nets'][pin]=wrong;nets[ref,pin]=wrong
    with self.assertRaises(ValueError):validate(spec,self.values,nets,self.fields)
 def test_wrong_driver_variant_and_rset(self):
  for ref,value in [('U32','CAT4004B'),('R82','3k 1%')]:
   spec=copy.deepcopy(self.spec);values=self.values.copy();fields=copy.deepcopy(self.fields)
   spec[ref]['value']=values[ref]=value;spec[ref]['mpn']=fields[ref]['MPN']=value
   with self.assertRaises(ValueError):validate(spec,values,self.nets,fields)
 def test_current_is_screen_not_qualification(self):
  r=screening(5.1654061)
  self.assertAlmostEqual(r['nominal_total_a'],.06012024,places=7)
  self.assertLess(r['conditional_total_screen_a'],.08)
  self.assertIsNone(r['guaranteed_maximum_current_a'])
  for v in [float('nan'),6,2]:
   with self.assertRaises(ValueError):screening(v)
 def test_actual_copper(self):self.assertTrue(check_board(p.LoadBoard(str(OUT/'handset.kicad_pcb')))['passed'])
 def test_cut_enable_copper_detected(self):
  tree=parse((OUT/'handset.kicad_pcb').read_text())
  tree[:]=[n for n in tree if not(isinstance(n,list) and n[0] in ('segment','via') and str(child(n,'net')[1])=='LCD_BL_EN')]
  path=Path('/tmp/backlight-cut-enable.kicad_pcb');path.write_text(dump(tree)+'\n')
  self.assertFalse(check_board(p.LoadBoard(str(path)))['passed'])
 def test_cut_channel_copper_detected(self):
  tree=parse((OUT/'handset.kicad_pcb').read_text())
  tree[:]=[n for n in tree if not(isinstance(n,list) and n[0] in ('segment','via') and str(child(n,'net')[1])=='LCD_K3')]
  path=Path('/tmp/backlight-cut-channel.kicad_pcb');path.write_text(dump(tree)+'\n')
  self.assertFalse(check_board(p.LoadBoard(str(path)))['passed'])
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BacklightTests))
 (OUT/'backlight-negative-tests.json').write_text(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful()),indent=2)+'\n')
 sys.exit(0 if result.wasSuccessful() else 1)
