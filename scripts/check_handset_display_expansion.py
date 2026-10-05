#!/usr/bin/env python3
"""CAD-derived display and expansion limits; never replace missing load evidence."""
import json
import math
import re
import xml.etree.ElementTree as ET
from check_handset_modem_power import ROOT, resistance, divider_range
from handset_display_contract import validate
from handset_expansion_contract import validate as validate_expansion
from handset_backlight_contract import validate as validate_backlight, screening

CONTRACT={
 'R31':{'1':'+3V3','2':'REG3_FB'},'R32':{'1':'REG3_FB','2':'GND'},
 'R34':{'1':'+5V_RF','2':'REG5_FB'},'R35':{'1':'REG5_FB','2':'GND'},
 'R41':{'1':'EXP_ILIM','2':'GND'},
 'U14':{'1':'+3V3','3':'EXP_PWR_EN','4':'EXP_FAULT_N','5':'EXP_ILIM','6':'EXP_3V3'},
 'J26':{'1':'+5V_RF','7':'LCD_3V0','8':'LCD_3V0','9':'LCD_3V0'},
}


def expansion_limits(ohms,tolerance):
    if not math.isfinite(ohms) or not math.isfinite(tolerance) or not 0<=tolerance<1:
        raise ValueError('Invalid ILIM resistor')
    low,high=ohms*(1-tolerance)/1000,ohms*(1+tolerance)/1000
    if low<15 or high>232:raise ValueError('ILIM resistor outside characterized range')
    # TI TPS2553 section 9.5.1, R in kohm and equation output in mA.
    return dict(minimum_a=25230/high**1.016/1000,
        nominal_a=23950/(ohms/1000)**.977/1000,maximum_a=22980/low**.94/1000)


def backlight(vsupply,vf,ohms):
    if not all(math.isfinite(v) for v in (vsupply,vf,ohms)) or min(vsupply,vf)<0 or ohms<=0:
        raise ValueError('Invalid backlight inputs')
    delta=max(0,vsupply-vf)
    return dict(branch_current_a=delta/ohms,resistor_dissipation_w=delta*delta/ohms)


def build_report(root=ROOT):
    spec={c['ref']:c for c in json.loads((root/'generated/connectivity.json').read_text())}
    xml=ET.parse(root/'generated/netlist.xml').getroot()
    values={c.attrib['ref']:c.findtext('value') for c in xml.findall('./components/comp')}
    nets={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in xml.findall('./nets/net') for n in net.findall('node')}
    validate(spec,values,nets)
    for ref,pins in CONTRACT.items():
        if values[ref]!=spec[ref]['value']:raise ValueError('CAD value mismatch: '+ref)
        for pin,net in pins.items():
            if spec[ref]['nets'][pin]!=net or nets.get((ref,pin))!=net:raise ValueError('Re-audit topology: '+ref+'.'+pin)
    for ref,expected in [('U14','TPS2553DBVR'),('U7','TPS63802DLAR'),('U10','TPS61023DRLR')]:
        if values[ref]!=expected:raise ValueError('Re-audit part model: '+ref)
    main=divider_range(resistance(values['R31']),resistance(values['R32']),[.495,.505])
    aux=divider_range(resistance(values['R34']),resistance(values['R35']),[.580,.610])
    aux_nom=.595*(1+resistance(values['R34'])[0]/resistance(values['R35'])[0])
    fields={c.attrib['ref']:{f.attrib['name']:f.text for f in c.findall('./fields/field')} for c in xml.findall('./components/comp')}
    validate_backlight(spec,values,nets,fields)
    validate_expansion(spec,values,nets,fields)
    current=screening(aux[1])
    routed=(root/'generated/display-routing.json').exists()
    return dict(scope='Component tolerance screening; panel logic/touch consumption and accessory demand remain unknown',
        expansion_current_limit=expansion_limits(*resistance(values['R41'])),
        expansion_enable='TCA9537 P0 with reset-default-off pull-down; P2 and FAULT gate signal isolation. See expansion-control-review.md',
        display_recommended_supply_max_v=3.3,display_regulated_range_v=[3*.985,3*1.015],
        display_range_conditions="U28 in regulation; excludes startup, ripple, thermal shutdown and load transients",
        display_interface_status=("Routed; physical continuity checked separately; electrical qualification pending" if routed else "Captured and placed; routing and hardware qualification pending"),main_pwm_reference_resistor_range_v=main,
        aux_pwm_reference_resistor_range_v=aux,aux_pwm_nominal_v=aux_nom,
        backlight_current_driver=current,
        backlight_reference_total_a=current['nominal_total_a'],
        panel_backlight_published_typical_a=.070,panel_backlight_published_max_a=.080,
        panel_minimum_led_vf_v=None,qualified_display_logic_current_a=None,qualified_touch_current_a=None,
        blocking_findings=[
            ('Display supply and translation are routed; qualify load, heat, power sequencing, touch option and shared-bus timing.' if routed else 'Dedicated LCD_3V0 and signal translation are captured; route and qualify load, heat, power sequencing, touch option and shared-bus timing.'),
            'CAT4004A current regulation is installed and routed; qualify absolute current across voltage/temperature, LED-short heat, exposed-pad assembly, GPIO startup and dimming timing. Typical current is not a qualified maximum.',
            'Expansion enable, polled fault input and hardware signal interlock are captured. Current limit does not establish permitted load; qualify startup, current, signal integrity, leakage, reset and brief-fault behavior. Shared-bus lockup requires external reset or power-off recovery; target firmware remains unintegrated.',
            'Ripple, feedback leakage, transients, resistor thermal derating and measured load profiles remain unqualified.'],
        fabrication_released=False)


if __name__=='__main__':
    report=build_report();(ROOT/'display-expansion-power-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
