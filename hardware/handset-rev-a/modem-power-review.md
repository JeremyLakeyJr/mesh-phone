# Modem startup/current audit and battery upgrade — 2026-09-27

**DO NOT FABRICATE.** The electrical screening and replacement-battery requirements are complete; replacement pack selection, battery-path redesign and physical qualification are not. No PCB routing or resistor values were changed in this step.

## User decision and replacement requirements

The user selected **a higher-current battery of similar capacity**, rather than a separately powered modem pod. New-build requirements are in [battery-upgrade-requirements.json](battery-upgrade-requirements.json): one protected 1S pack, approximately 3000 mAh, with a provisional **at least 5 A continuous-discharge target**. This target must cover the pack's PCM, leads and connector, not just a bare cell's marketing rating. Increase it if the final simultaneous-load budget requires more.

The existing screening case reaches 3.302 A at 3.0 V when output-voltage tolerance is included. Applying an initial 25% margin gives 4.127 A; 5 A is an engineering target above that result, **not a documented replacement-pack specification or a validated full-system budget**. The assumed 0.25 A of other battery load and 85% conversion efficiency remain unmeasured. The existing 4.17 V/charge-current policy is retained pending pack qualification.

MakerFocus data remains in `battery-qualification.json` as the legacy purchased-pack record. It is superseded for new-build selection, not edited to pretend the old pack has a higher rating.

## Candidate screening and pocketability

| Candidate | Published evidence | Disposition |
|---|---|---|
| Keeppower P1830RC | Protected 1S, 3000 mAh, 15 A continuous; cylindrical 18.8 mm diameter × 68.9 mm length, stated ±0.2 mm | Current capability is a candidate; cannot fit the existing 12 mm-deep battery space, before holder/clearances. Not selected. |
| Olimex BATTERY-LIPO3000mAh | 3000 mAh, 3 A maximum discharge, 135 × 45 × 5 mm | Below the provisional current target and outside the existing footprint. Rejected. |

Sources: [Keeppower manufacturer page](https://www.keeppower.com/product/max-15a-discharge-keeppower-18650-3000mah-protected-li-ion-rechargeable-battery-p1830rc/), [Olimex manufacturer page](https://www.olimex.com/Products/Power-Supply/Lipo-battery/BATTERY-LIPO3000mAh/).

Prefer a documented high-current pouch pack to retain the pocketable design. The current modeled allowance is **38 × 67 × 12 mm**; any replacement needs actual maximum dimensions including PCM, lead exits and swelling clearance. No compatible orderable pouch MPN has been frozen, and no enclosure-fit claim is made for a replacement.

## CAD-derived electrical findings

The checker reads exported KiCad values/nets and verifies them against `connectivity.json`, including forced-PWM mode, the divider topology and battery fuse/connector. It does not depend on manually copied resistor values alone.

- R60/R61 = 374 kΩ/100 kΩ, both 1%: nominal output **3.792 V**. Combining resistor and ±1% PWM reference corners gives **3.695–3.891 V**, before feedback leakage, ripple, transient error or wiring drop.
- R62/R63 = 390 kΩ/100 kΩ, both 1%: EN turn-on threshold/resistor corners give **3.714–4.132 V**; turn-off corners give **3.231–3.635 V**. These independent bounds are not a per-device hysteresis prediction.
- Applying an explicit symmetric 0.2 µA EN-input-current screening allowance expands the turn-on estimate to **3.636–4.211 V**. The upper value exceeds the nominal 4.17 V charge target. Q3 off-state leakage, temperature and wiring sag are still excluded, so this is not a guaranteed total worst-case envelope.
- TPS63070 also specifies a 3.0 V minimum input for startup when its output is below 3.0 V. Lowering the divider does not bypass this condition or solve excessive battery current.

Primary reference: [TI TPS63070 datasheet, electrical characteristics and precise-enable section](https://www.ti.com/lit/ds/symlink/tps63070.pdf).

The existing assumed 2 A modem burst produces this battery-current screening:

| Battery voltage | Current at nominal output | Current at high output-voltage corner |
|---|---:|---:|
| 3.00 V | 3.224 A | 3.302 A |
| 3.30 V | 2.954 A | 3.024 A |
| 3.70 V | 2.661 A | 2.724 A |
| 4.17 V | 2.390 A | 2.445 A |

Each includes the assumed 0.25 A other load. All exceed the legacy MakerFocus published 1.5 A operating current. Even an ideal 100% converter at the nominal output would require more than 1.5 A near full charge. A lower enable divider or optimistic efficiency alone cannot fix the mismatch. Exact modem variant/burst waveform and the final battery discharge curve must determine the new startup policy.

## Battery-path implications

F2 is currently **046701.5NRHF / 1.5 A** in series with all VBAT loads. It is a fuse, not a precision current limiter; its time/current curve and thermal derating must be coordinated with the new pack, wire and fault energy. Do not simply replace it with an arbitrary larger fuse. J1's JST PH footprint, harness, polarity, copper/vias and protection arrangement need qualification or replacement for the selected load. The higher-current battery decision does not qualify these existing parts.

These checks precede final U20 battery/modem feed routing. The replacement pack also needs documented charge/discharge temperature limits, NTC attachment and protection thresholds. The charger remains inhibited by its existing qualification policy.

## Executable checks and evidence

- `python3 scripts/check_handset_modem_power.py` writes [modem-power-report.json](modem-power-report.json), with source-input hashes, computed corners, current scenarios and open findings. Normal success means the audit ran, not that the power design passed qualification.
- `--require-compatible` returns nonzero for the current unresolved design. `check_handset_release.py` recomputes this audit so a stale saved report cannot clear manufacturing release.
- Six regression tests pass: known divider/leakage behavior, legacy-pack rejection, higher-current hypothetical remaining unqualified, lower divider not changing power demand, invalid assumptions/tolerance rejection, and exported-CAD value divergence rejection.
- Full artifact checks retain 2,104 passing integrity assertions, 393 unconnected items, 30 ERC findings, four existing USB hole-clearance findings and zero schematic parity findings. Hardware checks were not performed.

Next concrete work: freeze an orderable protected pouch pack that meets current and fit requirements; qualify/re-select F2, J1 and the harness, then revise startup thresholds and route the modem feeds against that selected power path. The decision to use a higher-current battery is already authorized and need not be asked again.
