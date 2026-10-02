#!/usr/bin/env python3
"""Regression checks for the startup/current screening and its CAD contract."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from check_handset_modem_power import ROOT, build_report, divider_range, evaluate, resistance, screen_candidates

class ModemPowerTests(unittest.TestCase):
    def setUp(self):
        spec=json.loads((ROOT/'generated/connectivity.json').read_text())
        self.values={c['ref']:c['value'] for c in spec}
        self.battery=json.loads((ROOT/'battery-qualification.json').read_text())
        self.policy=json.loads((ROOT/'charger-policy.json').read_text())

    def test_equal_divider_and_input_current(self):
        self.assertEqual(divider_range((10000,0),(10000,0),[.8]),[1.6,1.6])
        lo,hi=divider_range((10000,0),(10000,0),[.8],1e-6)
        self.assertAlmostEqual(lo,1.59);self.assertAlmostEqual(hi,1.61)

    def test_existing_pack_fails_even_near_full_charge(self):
        r=evaluate(self.values,self.battery,self.policy)
        self.assertTrue(all(not s['within_published_operating_limit'] for s in r['scenarios']))
        self.assertGreater(r['rising_with_symmetric_0_2ua_en_current_allowance_v'][1],r['charge_target_v'])

    def test_new_current_rating_does_not_qualify_hardware(self):
        self.battery['published']['operating_current_a']=5
        r=evaluate(self.values,self.battery,self.policy)
        self.assertTrue(all(s['within_published_operating_limit'] for s in r['scenarios']))
        self.assertFalse(r['fabrication_released']);self.assertTrue(r['blocking_findings'])

    def test_lower_divider_does_not_fix_pack_current(self):
        before=evaluate(self.values,self.battery,self.policy)
        self.values['R62']='300k 1%'
        after=evaluate(self.values,self.battery,self.policy)
        self.assertLess(after['rising_threshold_resistor_corner_v'][1],before['rising_threshold_resistor_corner_v'][1])
        self.assertEqual([r['high_output_corner_current_a'] for r in before['scenarios']],
                         [r['high_output_corner_current_a'] for r in after['scenarios']])

    def test_invalid_assumptions_and_missing_tolerance_rejected(self):
        with self.assertRaises(ValueError):resistance('390k')
        self.battery['screening_assumptions_not_measured']['modem_converter_efficiency']=0
        with self.assertRaises(ValueError):evaluate(self.values,self.battery,self.policy)

    def test_netlist_divergence_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'generated').mkdir()
            for rel in ['generated/connectivity.json','generated/netlist.xml']:
                shutil.copy2(ROOT/rel,root/rel)
            tree=ET.parse(root/'generated/netlist.xml')
            tree.find("./components/comp[@ref='R62']/value").text='300k 1%'
            tree.write(root/'generated/netlist.xml')
            with self.assertRaises(AssertionError):build_report(root)

    def test_pack_tolerance_and_current_do_not_imply_qualification(self):
        upgrade=json.loads((ROOT/'battery-upgrade-requirements.json').read_text())
        result=screen_candidates(upgrade,3.30174)[0]
        self.assertTrue(result['published_current_covers_screening_margin'])
        self.assertEqual(result['envelope_excess_width_length_thickness_mm'],[0,0,2.5])
        self.assertFalse(result['fits_stated_envelope'])
        self.assertFalse(result['qualified'])
        upgrade['existing_battery_envelope_mm']=[40,70,16]
        result=screen_candidates(upgrade,4.1)[0]
        self.assertTrue(result['fits_stated_envelope'])
        self.assertFalse(result['published_current_covers_screening_margin'])
        self.assertFalse(result['qualified'])

if __name__=='__main__':unittest.main()
