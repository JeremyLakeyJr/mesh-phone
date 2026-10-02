#!/usr/bin/env python3
"""Calculate modem power screening from exported CAD; never claim bench qualification."""
import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / 'hardware/handset-rev-a'
TI = 'https://www.ti.com/lit/ds/symlink/tps63070.pdf'
CONTRACT = {
    'U20': {'1':'GND','5':'MODEM_FB','14':'MODEM_REG_EN'},
    'R60': {'1':'MODEM_SUPPLY','2':'MODEM_FB'},
    'R61': {'1':'MODEM_FB','2':'GND'},
    'R62': {'1':'VBAT','2':'MODEM_REG_EN'},
    'R63': {'1':'MODEM_REG_EN','2':'GND'},
    'F2': {'1':'BAT_PACK_POS','2':'VBAT'},
    'J1': {'1':'BAT_PACK_POS','2':'GND'},
    'Q3': {'1':'MODEM_DISABLE','2':'GND','3':'MODEM_REG_EN'},
    'Q4': {'1':'SYS_EN','2':'GND','3':'MODEM_DISABLE'},
}

def resistance(value):
    m = re.fullmatch(r'(\d+(?:\.\d+)?)([kM]?)\s+(\d+(?:\.\d+)?)%', value)
    if not m:
        raise ValueError('Explicit resistance and tolerance required: '+value)
    r = float(m[1]) * {'':1, 'k':1000, 'M':1000000}[m[2]]
    t = float(m[3])/100
    if not r > 0 or not 0 <= t < 1:
        raise ValueError('Invalid resistor specification')
    return r, t

def divider_range(top, bottom, thresholds, leakage_a=0):
    """VBAT = VEN*(1+Rt/Rb)+I_EN*Rt; symmetric leakage is a screening allowance."""
    rt, tt = top; rb, tb = bottom
    values = [v*(1+r/s)+i*r for r,s,v,i in itertools.product(
        [rt*(1-tt),rt*(1+tt)], [rb*(1-tb),rb*(1+tb)],
        thresholds, [-leakage_a,leakage_a])]
    return [min(values),max(values)]

def evaluate(values, battery, policy):
    resistors = {ref: resistance(values[ref]) for ref in ('R60','R61','R62','R63')}
    a = battery['screening_assumptions_not_measured']
    efficiency = a['modem_converter_efficiency']
    peak = a['modem_output_peak_a']; other = a['other_battery_load_a']
    limit = battery['published']['operating_current_a']
    if not 0 < efficiency <= 1 or peak < 0 or other < 0 or limit <= 0:
        raise ValueError('Invalid current/efficiency assumptions')
    charge = 3.5 + int(policy['common_registers']['0x03'],16)*.01
    nominal = .8*(1+resistors['R60'][0]/resistors['R61'][0])
    output = divider_range(resistors['R60'],resistors['R61'],[.8*.99,.8*1.01])
    rising = divider_range(resistors['R62'],resistors['R63'],[.77,.83])
    falling = divider_range(resistors['R62'],resistors['R63'],[.67,.73])
    with_en_current = divider_range(resistors['R62'],resistors['R63'],[.77,.83],.2e-6)
    voltages = sorted(set([a['battery_voltage_v'],3.3,3.7,charge]))
    if any(v <= 0 for v in voltages):
        raise ValueError('Battery voltage must be positive')
    rows=[]
    for v in voltages:
        current=nominal*peak/(v*efficiency)+other
        high_current=output[1]*peak/(v*efficiency)+other
        rows.append(dict(battery_v=v,assumed_battery_current_a=current,
                         high_output_corner_current_a=high_current,
                         within_published_operating_limit=high_current<=limit,
                         allowable_modem_output_a_under_assumptions=max(0,limit-other)*v*efficiency/output[1],
                         starts_at_all_threshold_resistor_corners=v>=rising[1]))
    findings=[]
    if any(not row['within_published_operating_limit'] for row in rows):
        findings.append('Assumed modem burst exceeds published pack operating current; divider changes cannot fix the energy budget.')
    if any(not row['starts_at_all_threshold_resistor_corners'] for row in rows):
        findings.append('Existing EN divider does not guarantee startup across the screened battery voltages.')
    if with_en_current[1] > charge:
        findings.append('EN-current screening raises the upper turn-on estimate above the nominal charge target, before Q3 off-state leakage or wiring drop.')
    findings.extend(['Exact modem variant, burst waveform and efficiency are unqualified.',
                     'Q3 off-state leakage, temperature, input sag, copper and connector losses are not included.',
                     'Higher-current battery-path implementation and hardware validation remain unresolved.'])
    if not battery['physical_verification']['pack_qualified']:
        findings.append('Purchased battery remains physically unqualified.')
    return dict(scope='CAD-derived screening, not a guaranteed hardware operating envelope',
                source=TI, resistor_values={k:values[k] for k in resistors},
                output_nominal_v=nominal,output_reference_resistor_corner_v=output,
                rising_threshold_resistor_corner_v=rising,falling_threshold_resistor_corner_v=falling,
                rising_with_symmetric_0_2ua_en_current_allowance_v=with_en_current,
                charge_target_v=charge,assumptions=a,published_operating_limit_a=limit,
                scenarios=rows,blocking_findings=findings,fabrication_released=False)

def build_report(root=ROOT):
    spec={c['ref']:c for c in json.loads((root/'generated/connectivity.json').read_text())}
    netlist=ET.parse(root/'generated/netlist.xml').getroot()
    values={c.attrib['ref']:c.findtext('value') for c in netlist.findall('./components/comp')}
    nets={}
    for net in netlist.findall('./nets/net'):
        for node in net.findall('node'):
            nets[(node.attrib['ref'],node.attrib['pin'])]=net.attrib['name']
    assert values['U20']=='TPS63070RNMR', 'Re-audit converter model'
    for ref,pins in CONTRACT.items():
        assert values[ref]==spec[ref]['value'], 'CAD value mismatch: '+ref
        for pin,net in pins.items():
            assert spec[ref]['nets'][pin]==net and nets[(ref,pin)]==net, (ref,pin,'Circuit changed; re-audit equations')
    battery=json.loads((root/'battery-qualification.json').read_text())
    policy=json.loads((root/'charger-policy.json').read_text())
    report=evaluate(values,battery,policy)
    upgrade=json.loads((root/'battery-upgrade-requirements.json').read_text())
    target=upgrade['minimum_continuous_discharge_target_a']
    peak=max(row['high_output_corner_current_a'] for row in report['scenarios'])
    report['legacy_pack_identification']=battery['identification']
    report['candidate_screening']=screen_candidates(upgrade,peak)
    report['battery_upgrade']=dict(user_decision=upgrade['user_decision'],selected_pack_mpn=upgrade['selected_pack_mpn'],
        target_continuous_a=target,screening_peak_a=peak,screening_with_margin_a=peak*upgrade['screening_margin_factor'],
        target_covers_screening_with_margin=target>=peak*upgrade['screening_margin_factor'],
        target_is_qualified_pack_rating=False,existing_battery_fuse=values['F2'],existing_connector=spec['J1']['footprint'])
    report['blocking_findings'].extend(['Higher-current pack MPN, fit and protection are not frozen.',
        'Existing battery fuse '+values['F2']+' and J1/harness/copper require requalification for the higher-current architecture.'])
    report['input_sha256']={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in
        ['generated/connectivity.json','generated/netlist.xml','battery-qualification.json','charger-policy.json','battery-upgrade-requirements.json']}
    return report

def screen_candidates(upgrade, peak_a):
    """Screen published maxima only; passing these checks never qualifies a pack."""
    results=[]
    for candidate in upgrade['reviewed_candidates']:
        dimensions=candidate.get('dimensions_width_length_thickness_mm')
        if dimensions is None:
            continue
        maximum=[v+candidate['dimensional_tolerance_mm'] for v in dimensions]
        excess=[max(0,a-b) for a,b in zip(maximum,upgrade['existing_battery_envelope_mm'])]
        results.append(dict(mpn=candidate['mpn'],maximum_dimensions_width_length_thickness_mm=maximum,
            envelope_excess_width_length_thickness_mm=excess,
            fits_stated_envelope=not any(excess),
            published_current_covers_screening_margin=candidate['published_maximum_discharge_a']>=peak_a*upgrade['screening_margin_factor'],
            qualified=False,blocking_findings=candidate['qualification_blockers']))
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--require-compatible',action='store_true')
    args=parser.parse_args();report=build_report()
    (ROOT/'modem-power-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if args.require_compatible and report['blocking_findings']:
        raise SystemExit(1)
