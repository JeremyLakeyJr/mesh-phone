#!/usr/bin/env python3
"""Reject restoring the short clearance or silently shrinking required geometry."""
import json,sys,unittest
from pathlib import Path
import pcbnew as p
from check_handset_usb_connector import ROOT,inspect
OUT=Path(sys.argv.pop()) if len(sys.argv)>1 and not sys.argv[-1].startswith('-') else ROOT
class USBTests(unittest.TestCase):
 def board(self):return p.LoadBoard(str(OUT/'handset.kicad_pcb'))
 def usb(self,b):return next(f for f in b.GetFootprints() if f.GetReference()=='USB1')
 def test_installed_geometry(self):self.assertTrue(inspect(self.board())['passed'])
 def test_original_corner_fails(self):
  b=self.board()
  for q in self.usb(b).Pads():
   if q.GetNumber() in ['A1','B12','A12','B1']:q.SetShape(p.PAD_SHAPE_ROUNDRECT)
  r=inspect(b);self.assertFalse(r['passed']);self.assertTrue(all(v<.25 for v in r['ground_to_hole_clearance_mm'].values()))
 def test_shrunk_hole_rejected(self):
  b=self.board()
  for q in self.usb(b).Pads():
   if q.GetAttribute()==p.PAD_ATTRIB_NPTH:q.SetDrillSize(p.VECTOR2I(p.FromMM(.5),p.FromMM(.5)))
  self.assertFalse(inspect(b)['passed'])
 def test_shrunk_land_rejected(self):
  b=self.board();q=next(q for q in self.usb(b).Pads() if q.GetNumber()=='A1');q.SetSize(p.VECTOR2I(p.FromMM(.4),p.FromMM(.8)));self.assertFalse(inspect(b)['passed'])
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(USBTests));(OUT/'usb-connector-tests.json').write_text(json.dumps(dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),passed=r.wasSuccessful()),indent=2)+'\n');sys.exit(not r.wasSuccessful())
