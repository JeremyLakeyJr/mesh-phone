#!/usr/bin/env python3
"""Budget screening, not evidence of purchased-pack or hardware qualification."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def evaluate(record,policy):
    a=record['screening_assumptions_not_measured']; p=record['published']
    assert 0 < a['modem_converter_efficiency'] <= 1 and a['battery_voltage_v'] > 0
    modem=a['modem_output_voltage_v']*a['modem_output_peak_a']/(a['battery_voltage_v']*a['modem_converter_efficiency'])
    remaining=max(0,p['operating_current_a']-a['other_battery_load_a'])
    target=3.5+int(policy['common_registers']['0x03'],16)*0.01
    return {
      'scope':'Illustrative modem load screening, not measured worst-case budget',
      'charge_target_v':round(target,5),
      'charge_target_at_plus_0_5_percent_v':round(target*1.005,5),
      'below_4_2v_at_regulation_tolerance':target*1.005<=4.2,
      'scenario_battery_current_a':round(modem+a['other_battery_load_a'],4),
      'scenario_within_published_operating_limit':modem+a['other_battery_load_a']<=p['operating_current_a'],
      'maximum_modem_output_a_under_assumptions':round(remaining*a['battery_voltage_v']*a['modem_converter_efficiency']/a['modem_output_voltage_v'],4),
      'physical_pack_qualified':record['physical_verification']['pack_qualified'],
      'fabrication_released':False}
if __name__=='__main__':
    folder=ROOT/'hardware/handset-rev-a'
    r=evaluate(json.loads((folder/'battery-qualification.json').read_text()),json.loads((folder/'charger-policy.json').read_text()))
    assert r['below_4_2v_at_regulation_tolerance'], 'Voltage target exceeds 4.2V with tolerance'
    (folder/'battery-budget-report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))
    # A rejected illustrative scenario is a design finding, not a broken checker.
