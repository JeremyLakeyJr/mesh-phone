#!/usr/bin/env python3
import unittest
import copy
import json
import xml.etree.ElementTree as ET
from check_handset_modem_power import ROOT
from handset_display_contract import validate
from check_handset_display_expansion import expansion_limits,backlight,build_report

class PeripheralPowerTests(unittest.TestCase):
    def test_ilim_corners_include_resistor_tolerance(self):
        nominal=expansion_limits(100000,0);corners=expansion_limits(100000,.01)
        self.assertLess(corners['minimum_a'],nominal['minimum_a'])
        self.assertGreater(corners['maximum_a'],nominal['maximum_a'])
        self.assertLess(corners['maximum_a'],.31)
        self.assertGreater(corners['minimum_a'],.23)

    def test_short_fault_exposes_old_resistor_rating(self):
        r=backlight(5.165406,0,148.5)
        self.assertGreater(r['resistor_dissipation_w'],.1)
        self.assertLess(r['resistor_dissipation_w'],.33)
        self.assertEqual(backlight(3,3.2,150)['branch_current_a'],0)

    def test_invalid_resistor_rejected(self):
        for ohms in (0,1000,300000,float('nan')):
            with self.assertRaises(ValueError):expansion_limits(ohms,.01)

    def test_regulated_display_range(self):
        report=build_report()
        self.assertGreater(report['display_regulated_range_v'][0],2.5)
        self.assertLess(report['display_regulated_range_v'][1],3.3)

    def test_unsafe_interface_mutations_rejected(self):
        spec={c['ref']:c for c in json.loads((ROOT/'generated/connectivity.json').read_text())}
        xml=ET.parse(ROOT/'generated/netlist.xml').getroot()
        values={c.attrib['ref']:c.findtext('value') for c in xml.findall('./components/comp')}
        nets={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')}
        validate(spec,values,nets)
        # Mutate both representations: agreement alone must not legitimize bad wiring.
        for ref,pin,wrong in [('U30','1','GND'),('J26','7','+3V3'),('J26','37','SPI_SCK'),('U31','3','+3V3'),('U29','15',None)]:
            with self.subTest(ref=ref,pin=pin):
                badspec=copy.deepcopy(spec);badnets=nets.copy()
                badspec[ref]['nets'][pin]=wrong;badnets[(ref,pin)]=wrong
                with self.assertRaises(ValueError):validate(badspec,values,badnets)

    def test_missing_panel_data_remains_unqualified(self):
        report=build_report()
        self.assertIsNone(report['panel_minimum_led_vf_v'])
        self.assertIsNone(report['qualified_display_logic_current_a'])
        self.assertGreater(report['main_pwm_reference_resistor_range_v'][1],3.3)
        self.assertFalse(report['fabrication_released'])

if __name__=='__main__':unittest.main()
