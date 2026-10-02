# Supervisor distribution routing — 2026-09-25

The separate charging supervisor's power, ground, I²C and programming
connections are now routed. **This completes the routing step, not working
powered-off charging or fabrication release.** STM32 target firmware and
hardware qualification are still required.

## Completed layout

- Connect U26 IN/EN and C77 to the charger's VSYS output at C6/U3, upstream
  of SW19. This branch powers the supervisor, not the handset/modem load.
- Connect PWR_AON_3V0 to U25, U27's B side, local capacitors, private-bus/reset
  pull-ups, TP2 and the existing U24/C60/R66/R69 power-entry island.
- Connect U27's switched supply/enable and host pull-ups R3/R4 to the main
  regulator output at C21/U7. This does not complete all main-rail distribution.
- Route both private charger-bus signals from U25 through R76/R77 to U24/U3.
- Route the isolated host interface between U25 and U27. Its B side still has
  no external pull-ups. Connect U27's A-side signals through the R3/R4 host
  bus to ESP32 U1 pins 17/18. Other host I²C peripherals remain outside scope.
- Route NRST and SWDIO/SWCLK to TP6/TP4/TP5, plus TP2 reference and TP3 ground.
- Move only C77–C82 to improve local bypass placement. Add eleven nearby
  ground-return vias and an In1.Cu ground region connected to the existing
  power-entry ground trunk and regulator return. Refill zones before checking.

All 847 pre-existing track/via geometries and all IC placements are preserved.
577 track/via items and one ground zone are added. Long supply branches use
0.25 mm VSYS and switched-supply traces, 0.20 mm AON distribution to the power
entry, and 0.15 mm local necks/control traces. These dimensions are not a
qualification of regulator current capacity or the full handset power budget.
The trackball opening and existing copper remain clear under native rules.

Manufacturer layout references: [TI TPS7A02](https://www.ti.com/lit/ds/symlink/tps7a02.pdf)
requires nearby input/output capacitors; [TI TCA9800](https://www.ti.com/lit/ds/symlink/tca9800.pdf)
specifies the separate supply bypass and B-side pull-up restrictions;
[ST STM32G031](https://www.st.com/resource/en/datasheet/stm32g031g8.pdf)
provides supply/decoupling requirements. Effective capacitor values, rail
startup and I²C rise times still need electrical qualification.

## Verification

`check_handset_supervisor_routing.py` checks 67 explicit pad endpoints across
13 net groups using KiCad copper connectivity, including zone/via connections.
All pass. It also verifies the eleven local ground vias are connected and
within 2.2 mm of their pad centers (actual distances are recorded in the report).
Deleting the private SCL copper or VSYS copper in temporary board copies makes
the checker fail as expected; labels alone cannot satisfy the check.

The existing 118-pad power-entry, 26-pad main-regulator and independent
charge-inhibit continuity checks also pass. All 2,104 schematic/PCB integrity
checks pass. Native results: zero parity differences, 30 unchanged ERC
findings, four pre-existing USB1 hole-clearance findings and **483 unconnected
items**, down from 499. No new placement/clearance findings were introduced.

Evidence: `generated/supervisor-routing.json`,
`generated/supervisor-routing-check.json`,
`generated/supervisor-routing-negative-tests.json`, and native reports.

## Next step

An [inhibited STM32G031 target](../../firmware/power/stm32g031/README.md) is now
cross-built; it cannot authorize charging and has not been hardware-tested.
Complete operational target firmware: bounded private-bus I²C,
direct PA0 charge permission, watchdog/BOR/reset configuration, durable inhibit
and diagnostic storage, and the isolated host protocol with expiring legacy-USB
permission. Keep `exact_pack_qualified=false` until the battery/NTC/current
requirements are verified. The portable host-tested controller is not a flashed
STM32 application.

Then validate regulator dropout/transients, capacitor DC bias, bus rise times,
unpowered-host leakage, reset/brownout shutdown, watchdog behavior and recovery
on hardware. Routing completion does not resolve the MakerFocus pack's physical
verification or modem peak-current mismatch. Other PCB sections and 483
unconnected items remain open; do not fabricate or power this revision.
