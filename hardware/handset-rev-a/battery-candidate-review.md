# Higher-current battery candidate screening — 2026-09-27

CU-JAS427 is the preferred **prototype investigation candidate**, not a production selection. The user approved changing to a higher-current pack near 3000 mAh. `battery-upgrade-requirements.json` preserves that decision and keeps `selected_pack_mpn` null. No PCB, enclosure, charger-current or charging-permission change is authorized by this screening result alone.

## Primary evidence

- [BatterySpace CU-JAS427](https://www.batteryspace.com/polymer-li-ion-battery-pack-3-7v-3000mah-11-1wh-5a-rate.aspx): protected 1S2P, 3000 mAh, 5 A maximum discharge, 600 mA standard charge, 3 A maximum charge, 4.2 V charge cutoff and 2.75 V discharge cutoff. Published dimensions are 65 × 36 × 13 mm ±1.5 mm; leads are 6-inch 22 AWG. Listing explicitly restricts it to prototypes and states the pack has not passed UN38.3.
- [Linked PCB-S1A6 protection](https://www.batteryspace.com/PCB-for-3.7V-Li-Ion-Battery-5.0A-limit.aspx): 5 A continuous, 7–9 A overcurrent trip, 4.300 ±0.050 V overcharge and 2.40 ±0.100 V overdischarge protection. These emergency thresholds are not normal operating targets. Trip delay and coordination remain unverified.
- [Linked NTC](https://www.batteryspace.com/component-ntc-thermistors-10kohm-1-shape-1-30-awg-50mm---ul-listed.aspx): 10 kΩ ±1%, B3435 ±1%. Nominally matches the intended thermistor characteristic; attachment, reference wire and complete temperature limits still need qualification.
- [Linked PL-703562-2C cell](https://www.batteryspace.com/polymer-li-ion-cell-3-7v-1500mah-703562-2c-5-55wh-3a-rate---un38-3-passed--.aspx): updated cell dimensions 68 × 35 × 6.8 mm ±1 mm contradict the shorter pack listing. Its 3 A discharge rating is temperature-limited to 0–45°C. Cell certification does not certify the assembled pack.
- [Molex 2053380002](https://www.molex.com/en-us/products/part-detail/2053380002): candidate J1 replacement, 2 mm pitch, 2.6 mm mated height, positive lock and 6.5 A maximum/contact. The rating requires mating-harness and operating-condition verification. Existing KiCad footprint is `Connector_Molex:Molex_Pico-Lock_205338-0002_1x02-1MP_P2.00mm_Horizontal`; it is now installed as J1 with local continuity and native DRC checked; current and assembly qualification remain open.

## Calculated screening

The CAD-derived modem scenario reaches approximately 3.302 A battery input. Applying the existing 1.25 screening margin gives 4.127 A, below the candidate's published 5 A maximum. This is a conditional calculation, not proof of complete handset load, cold operation, transient behavior or thermal capability.

In width/length/thickness order, the published maximum pack envelope is 37.5 × 66.5 × 14.5 mm. Compared with the current 38 × 67 × 12 mm allowance, thickness exceeds the allowance by **2.5 mm**, before swelling, lead exit and assembly clearance. The contradictory cell length also prevents trusting the nominal in-plane fit. Do not resize the pocketable enclosure around this unverified drawing.

`check_handset_modem_power.py` now exports these current and fit results under `candidate_screening`; passing either cannot set `qualified` or release fabrication. Existing legacy-pack results remain separate, avoiding substitution of this candidate's rating for the purchased MakerFocus pack.

## Remaining implementation sequence

1. Obtain a controlled pack drawing resolving the length contradiction, plus pack current/temperature limits, PCM trip timing and NTC wiring/attachment details. A sample must establish actual dimensions and polarity. No vendor request has been sent and no pack has been ordered.
2. Confirm a complete mating harness for the Pico-Lock candidate and temperature/current derating. J1 replacement, local routing, native parity and clearance checks are complete; see [connector implementation review](battery-connector-review.md).
3. Coordinate F2 with normal load, modem inrush, ambient derating, PCM trip delay and harness fault withstand. The installed 1.5 A fuse remains unsuitable for the proposed load; a larger fuse must not be treated as a current limiter.
4. Qualify copper/returns and route U20's external battery feed. Resolve its startup thresholds and measure sag, inrush and temperature with the complete load.
5. Reconcile the qualified maximum pack envelope with populated board clearance and the case; then finish charge-temperature and powered-off charging validation. The existing 4.17 V policy and inhibited charging state remain in force.

**DO NOT FABRICATE OR POWER:** candidate screening does not close the battery, power-path or other release blockers.
