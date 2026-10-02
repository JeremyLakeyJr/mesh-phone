#!/usr/bin/env python3
import unittest
from check_handset_battery_copper import serial_route


class CopperTests(unittest.TestCase):
    def test_analytical_resistance_and_scaling(self):
        segment=[((0,0),(10,0),1)]
        r=serial_route(segment,(0,0),(10,0))['resistance_ohm']
        self.assertAlmostEqual(r,0.004925714285714286)
        self.assertAlmostEqual(serial_route(segment,(0,0),(10,0),70)['resistance_ohm'],r/2)
        self.assertAlmostEqual(serial_route(segment,(0,0),(10,0),35,70)['resistance_ohm'],r*1.1965)

    def test_broken_or_branched_route_rejected(self):
        route=[((0,0),(1,0),1),((1,0),(2,0),1)]
        self.assertEqual(serial_route(route,(0,0),(2,0))['length_mm'],2)
        for bad in (route[:1],route+[((1,0),(1,1),1)]):
            with self.assertRaises(ValueError):serial_route(bad,(0,0),(2,0))

    def test_invalid_dimensions_rejected(self):
        with self.assertRaises(ValueError):serial_route([((0,0),(1,0),0)],(0,0),(1,0))
        with self.assertRaises(ValueError):serial_route([((0,0),(1,0),1)],(0,0),(1,0),0)


if __name__=='__main__':unittest.main()
