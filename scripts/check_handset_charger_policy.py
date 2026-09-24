#!/usr/bin/env python3
"""Check the register contract against BQ25186/TCA9536 field encodings.

This does not implement an ESP32 driver or validate hardware behavior.
"""
import json
from pathlib import Path


def validate(policy):
    errors = []
    def require(ok, message):
        if not ok:
            errors.append(message)
    regs = {int(k, 16): int(v, 16) for k, v in policy['common_registers'].items()}
    require(policy['charger_address_7bit'] == 0x6a, 'charger I2C address')
    require(policy['expander_address_7bit'] == 0x41, 'expander I2C address')
    require(regs[3] == 0x44, '4.18V regulation target')
    require(regs[5] == 0x25, 'termination/VINDPM/thermal regulation')
    require(regs[6] == 0x56, '1A charger discharge limit and 3V UVLO')
    require(regs[7] & 0x80 != 0, 'TS hardware protection must remain enabled')
    require((regs[7] >> 2) & 3 == 2, '12-hour safety timer required')
    require(regs[7] & 3 == 1, '160-second hardware-reset watchdog required')
    require(regs[7] & 0x10 != 0, 'slow timer while input/thermal limited')
    require(regs[10] == 0x40, '4.5V SYS with DPPM enabled')
    require(regs[11] == 0xe0, '5/45C thresholds; retain cool/warm derating')
    require(policy['expander_startup'] == [['0x01','0x00'], ['0x03','0x0c'], ['0x50','0x40']],
            'preload low outputs before changing expander direction')
    expected = {'unknown_or_detached': (100, 10, False, False),
                'legacy_configured_500mA': (400, 300, True, True),
                'type_c_1p5A_or_3A': (665, 500, True, False),
                'fault': (100, 10, False, False)}
    ilim_values = (50,100,200,300,400,500,665,1050)
    for name, values in expected.items():
        mode = policy['modes'][name]
        ilim, ichg = int(mode['ilim'],16), int(mode['ichg'],16)
        code = ichg & 0x7f
        charge_ma = code + 5 if code <= 30 else 40 + (code - 31)*10
        enabled = not bool(ichg & 0x80)
        actual = (ilim_values[ilim & 7], charge_ma, enabled, mode['legacy_enable'])
        require(actual == values, name + ': incorrect source/current permissions')
        require(enabled == mode['charge_enable'], name + ': CE/software-disable disagreement')
        require(ilim & 0xf8 == 0x48, name + ': reset timing bits changed')
    return errors


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1]/'hardware/handset-rev-a/charger-policy.json'
    policy = json.loads(path.read_text())
    errors = validate(policy)
    if errors:
        raise SystemExit('\n'.join(errors))
    # Deliberate unsafe mutations must be rejected, not just a golden-file check.
    import copy
    for field, value in [('0x07','0x1b'), ('0x0b','0x00'), ('0x05','0xa5')]:
        broken = copy.deepcopy(policy)
        broken['common_registers'][field] = value
        assert validate(broken), field + ': failed to reject unsafe policy'
    broken = copy.deepcopy(policy)
    broken['modes']['type_c_1p5A_or_3A']['legacy_enable'] = True
    assert validate(broken), 'failed to reject bypass of CC withdrawal'
    broken = copy.deepcopy(policy)
    broken['expander_startup'].reverse()
    assert validate(broken), 'failed to reject unsafe GPIO initialization order'
    print('Charger register contract and five negative tests passed; firmware/bench validation remain.')
