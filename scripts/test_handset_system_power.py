#!/usr/bin/env python3
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from check_handset_system_power import ROOT, build_report, scenario


class SystemPowerTests(unittest.TestCase):
    def test_branch_separation(self):
        r=scenario(3,1,.25,2,3.9,1)
        self.assertAlmostEqual(r['handset_branch_a'],4.55/3)
        self.assertAlmostEqual(r['modem_branch_a'],2.6)
        self.assertAlmostEqual(r['total_battery_a'],4.55/3+2.6)

    def test_unknown_loads_do_not_become_zero_or_qualified(self):
        r=build_report()
        self.assertTrue(r['unresolved_load_profiles'])
        self.assertFalse(r['fabrication_released'])
        self.assertGreater(r['esp32_reference_case']['handset_branch_a'],r['legacy_other_load_allowance_a'])
        self.assertEqual(r['configured_handset_ocp_code'],1)

    def test_lower_modem_load_does_not_fix_handset_branch(self):
        before=scenario(3,1.5,.25,2,3.9,.85)
        after=scenario(3,1.5,.25,0,3.9,.85)
        self.assertEqual(before['handset_branch_a'],after['handset_branch_a'])
        self.assertLess(after['total_battery_a'],before['total_battery_a'])

    def test_topology_change_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'generated').mkdir()
            for name in ['system-power-inputs.json','generated/connectivity.json','generated/netlist.xml']:
                shutil.copy2(ROOT/name,root/name)
            p=root/'generated/connectivity.json';s=json.loads(p.read_text())
            next(c for c in s if c['ref']=='U20')['nets']['12']='VSYS'
            p.write_text(json.dumps(s))
            with self.assertRaises(ValueError):build_report(root)

    def test_invalid_efficiency_rejected(self):
        for efficiency in (0,1.1,float('nan')):
            with self.assertRaises(ValueError):scenario(3,1,0,2,3.9,efficiency)


if __name__=='__main__':unittest.main()
