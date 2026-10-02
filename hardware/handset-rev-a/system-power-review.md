# Handset and modem power envelope — 2026-09-27

The previous modem calculation's **0.25 A other-load allowance is not a complete handset budget**. The new `system-power-inputs.json` inventories 18 load groups with unresolved current profiles explicitly marked null. `system-power-report.json` separates the charger-fed handset branch from the modem's direct fused-battery branch. Unknown peripheral loads are not treated as zero, and no operating mode is qualified by this work.

## Verified sources and topology

- [ESP32-S3-WROOM-1 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf), table 6-4: 355 mA at 3.3 V for the specified 802.11b transmit case at 25°C and 100% TX duty. At assumed 85% conversion efficiency and 3 V battery input, that represents approximately **0.459 A** battery current before other loads. This reference case alone exceeds the old 0.25 A allowance; it is not a worst-case bound for the complete populated handset.
- [BQ25186 datasheet](https://www.ti.com/lit/ds/symlink/bq25186.pdf), register 0x06 and electrical characteristics: current policy `0x56` selects the nominal 1 A discharge setting, with a listed 1.05 A typical OCP threshold. This is not a guaranteed continuous-current rating. U3 BAT connects to VBAT and SYS feeds U7/U10 and the supervisor. U20 instead draws directly from VBAT, so increasing U3's limit would not protect or limit the modem branch.
- [TPS63802 datasheet](https://www.ti.com/lit/ds/symlink/tps63802.pdf): 2 A output capability is stated for input ≥2.3 V and 3.3 V output. This component capability does not authorize every peripheral to draw its maximum simultaneously.
- CAD also ties U14's expansion enable to +3V3. Do not assume software can switch off expansion power with the current topology. Its fault-monitoring connection and current limit still require resolution.

The checker validates these supply connections against both the connectivity specification and exported schematic netlist, and decodes the actual charger-policy register. A topology mismatch stops the calculation.

## Sensitivity results

These are hypothetical simultaneous battery-only rail loads, **not measured product operating modes**. They assume 85% conversion efficiency, ideal SYS tracking, a 2 A modem output demand and the existing calculated 3.891 V modem-output corner. They exclude additional quiescent load, FET/wiring drop, inrush and USB load sharing. Zero auxiliary current means a deliberately disabled-load test case, not an unknown display load silently omitted from qualification.

At 3 V battery input:

| 3.3 V load | 5 V load | Handset branch | Modem branch | Shared battery current |
|---:|---:|---:|---:|---:|
| 0.75 A | 0.25 A | 1.461 A | 3.052 A | 4.513 A |
| 1 A | 0 A | 1.294 A | 3.052 A | 4.346 A |
| 2 A | 0 A | 2.588 A | 3.052 A | 5.640 A |

All three cross the configured handset OCP typical threshold; the last also crosses the provisional 5 A pack target. They expose separate constraints that a larger fuse alone cannot fix. The script evaluates 60 combinations across battery voltage and rail-current test points.

## Completed and remaining work

- Completed: explicit load inventory, separate branch calculations, policy decoding, CAD/netlist contracts, 60-case sensitivity report and manufacturing-release integration.
- Five regression tests verify branch separation, unknown-load handling, independent modem/handset demand, topology-change rejection and invalid assumptions.
- Remaining: actual peak, continuous and startup profiles for the listed loads; exact modem, display/backlight, audio, card and external-module demands; permitted concurrency and its enforcement; converter efficiency and voltage sag; charger FET temperature, pack/harness/copper qualification and fuse coordination.

Next, resolve the display/backlight and expansion demands and establish enforceable operating modes. Then decide whether the handset branch can use a qualified higher charger-discharge setting or needs a different distribution circuit. Do not raise the charger limit or fit a larger F2 until that decision is supported. The existing inhibited charging state, fuse, PCB and features are unchanged by this audit. **DO NOT FABRICATE OR POWER.**
