# Independent charge inhibit — 2026-09-25

The reset-time CE design gap is now addressed in the schematic, routed PCB and
portable controller interface. Hardware response timing and STM32 integration
remain unqualified; this is **not a fabrication or power-on release**.

## Circuit and routing

Q8 (AO3400A, SOT-23) is in series with the existing Q5 CE pull-down:
`U3.4 /CE → Q5 drain/source → CHG_CE_RETURN → Q8 drain/source → GND`.
Q5 still receives U24's CHG_ENABLE. Q8 receives U25 PA0, UFQFPN28 pin 6,
on CHG_ARM. R79, RC0402FR-074K7L, 4.7k 1%, pulls that gate to ground locally.
R6 continues to pull /CE up to VSYS.

| Expander permission | STM32 permission | Resulting /CE permission |
| --- | --- | --- |
| Low | Low or high | Disabled |
| High | Low | Disabled |
| High | Reset/high impedance | Disabled after gate discharge |
| High | High | Enabled, subject to charger registers/temperature/input conditions |

Both NMOS body diodes point from source toward drain. Q8's source is grounded;
its body diode cannot bypass the off transistor from CHG_CE_RETURN to ground.
A supervisor reset therefore need not reset U24 to remove charge permission.
A CPU that hangs while actively driving PA0 high still needs an independent
watchdog reset; this circuit is not a watchdog by itself.

The STM32 default GPIO analog state and debug-pin exceptions are documented in
[ST RM0444 §7.3.1](https://www.st.com/resource/en/reference_manual/rm0444-stm32g0x1-advanced-armbased-32bit-mcus-stmicroelectronics.pdf).
PA0 is separate from the debug pins. Firmware must not configure retention,
alternate functions or pull-ups on CHG_ARM. Provision boot/reset option bytes
and validate the actual device's power-on, NRST, BOR and IWDG behavior.

[AOS specifies AO3400A](https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf)
with RDS(on) characterized at 2.5 V gate drive. The intended control rail is
3.0 V. Gate drive, off leakage and /CE rise must be verified at minimum rail,
maximum temperature and during brownout; threshold voltage is not an on-state
resistance specification. /CE thresholds are in
[TI BQ25186 §5.5](https://www.ti.com/lit/ds/symlink/bq25186.pdf).

The routed changes include U25.6–R79.1–Q8.1, Q5.2–Q8.3 and both new ground
returns. CHG_ARM passes around the trackball opening with the board's 0.5 mm
copper-edge clearance. All existing footprints are retained. Only Q5's former
ground stub (two segments and one unused via) was removed; the other 789 copper
items retain their original geometry. Exact changes are recorded in
`generated/charge-inhibit-update.json`; MPNs are in `charge-inhibit-bom.csv`.

## Controller changes

`PowerIO::set_charge_arm()` is an independent GPIO operation, never an I2C
expander write. Its default implementation fails, so an unported HAL cannot
silently enable charging. STM32 HAL implementation and target build remain open.

- At startup, remove permission before accessing storage or I2C. Preload the
  output latch low before selecting PA0 push-pull output, with no pull-up.
- Raise CHG_ARM only after policy/status validation and successful expander
  enable readback. Steady polling does not cycle either enable.
- Remove CHG_ARM before I2C shutdown on faults, source changes or shutdown, and
  on temperature/input-not-ready transitions. A broken I2C bus cannot prevent
  a functioning CPU/GPIO from dropping Q8.
- Keep the existing durable inhibition marker; reset does not automatically
  reauthorize charging. Unqualified packs never receive permission.

The legacy ESP-IDF adapter intentionally has no implementation of this GPIO
operation and cannot start this controller. It is not a driver for the current
supervisor PCB.

## Checks completed

- 2,104 schematic/PCB integrity assertions, zero parity differences.
- Twelve independent pin contracts, four topology truth-table cases and five
  negative tests, including reversed Q8 drain/source and a bypassed second gate.
- Physical copper continuity for all four affected groups, including the full
  STM32-to-gate path. Expanded local power-entry check passes for 118 pads.
- C++17 host tests with strict warnings and UndefinedBehaviorSanitizer cover
  retained expander state, I2C failure, failed/missing arm HAL, startup failure,
  reset inhibition, temperature suspension and no steady-state enable cycling.
- Native results remain 30 ERC findings, four pre-existing USB1 hole-clearance
  findings and 499 unconnected items. No new placement/clearance findings.

## Next step

The [supervisor distribution routing](supervisor-routing-review.md) is now
complete for these endpoints. Next implement the STM32 HAL,
watchdog/BOR provisioning, durable storage and expiring legacy-USB permission.
The legacy-input expander output can still survive a reset; Q8 inhibits battery
charging but does not itself revoke that input permission.

Before charging a pack, measure /CE shutdown and charge-current decay during
reset, bus hang, brownout and power transitions with the expander deliberately
latched high. Qualify pull-down discharge/leakage, watchdog timeout and restart
inhibition. The pack/NTC/current-budget blockers are unchanged.
