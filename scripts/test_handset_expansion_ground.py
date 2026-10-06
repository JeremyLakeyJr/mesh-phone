#!/usr/bin/env python3
"""Check the installed return and prove continuity depends on the new ground pours."""
import json,sys,tempfile,unittest
from pathlib import Path
import pcbnew as p
from cad_sexpr import parse,dump,child
from check_handset_expansion import ROOT,check_board
OUT=Path(sys.argv.pop()) if len(sys.argv)>1 and not sys.argv[-1].startswith('-') else ROOT
class GroundTests(unittest.TestCase):
 def test_actual_return(self):
  b=p.LoadBoard(str(OUT/'handset.kicad_pcb'))
  self.assertTrue(check_board(b)['passed'])
  self.assertEqual({z.GetLayer() for z in b.Zones() if z.GetZoneName()=='Expansion ESD return'},{p.In1_Cu,p.In2_Cu})
 def test_missing_pours_break_esd_return(self):
  tree=parse((OUT/'handset.kicad_pcb').read_text())
  tree[:]=[n for n in tree if not(isinstance(n,list) and n[0]=='zone' and child(n,'name') and child(n,'name')[1]=='Expansion ESD return')]
  with tempfile.TemporaryDirectory(prefix='esd-return-negative-') as d:
   f=Path(d)/'handset.kicad_pcb';f.write_text(dump(tree)+'\n');b=p.LoadBoard(str(f));p.ZONE_FILLER(b).Fill(b.Zones())
   ground=next(g for g in check_board(b)['groups'] if g['net']=='GND')
   self.assertFalse(ground['passed'])
   self.assertTrue({'U15.3','U15.8','U16.3','U16.8'} & set(ground['disconnected']))
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GroundTests))
 (OUT/'expansion-ground-tests.json').write_text(json.dumps(dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),passed=r.wasSuccessful()),indent=2)+'\n');sys.exit(not r.wasSuccessful())
