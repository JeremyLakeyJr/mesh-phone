# Charger controller integration

`charger.hpp` is a portable C++17 control core for the saved BQ25186/TCA9536
circuit. It is **not installed ESP32 firmware**, and is not authorization to
power the incomplete PCB. No ESP32 firmware target existed in this repository.

The controller starts with CE and legacy authorization low, preloads expander
outputs before configuring direction, verifies register writes and polls the
read-to-clear fault registers. Source loss removes charging permission; valid
source return can recover within the same fault-free session. A fault, register
reset, bus failure or missed 1-second deadline latches inhibition. Steady-state
polling does not toggle CE or restart the charge safety timer.

The 4.17V setpoint incorporates BQ25186's +0.5% regulation tolerance below
4.2V. Limits otherwise match `hardware/handset-rev-a/charger-policy.json`.
Temperature derating/suspension remains enabled in hardware. TS-open/UVLO and
historical battery faults conservatively require service review, so automatic
deeply depleted-pack recovery is **not yet implemented**.

A [cross-built STM32 commissioning target](stm32g031/README.md) now includes
the core, bounded private-bus I²C, watchdog and GPIO shutdown. It deliberately
refuses charging: durable storage and operational host permissions remain open.
It has not been flashed or hardware-tested.

## Integration requirements

Target owner is now the separate STM32G031 supervisor; see
[hardware capture](../../hardware/handset-rev-a/power-supervisor-review.md).
The `esp_idf/` direct U3/U24 adapter is a superseded host-integration example,
not the driver for this PCB. Its fake-SDK tests do not constitute an ESP-IDF
target build. The ESP32 must communicate through the supervisor protocol.

- Implement `set_charge_arm(bool)` on U25 PA0 (pin 6) as a direct GPIO
  operation independent of I2C. Preload low before output mode. The default
  implementation returns failure, preventing startup with an unported HAL.
  The supervisor power/I2C/SWD wiring is now routed; the inhibited commissioning implementation is built, but operational firmware
  remains incomplete. The core disarms before bus/storage operations and raises this permission
  only after verified expander enable. Reset high impedance relies on local R79.
- Supply bounded-time I2C read/write operations at 7-bit addresses 0x6A and 0x41.
  Serialize this owner with the rest of the bus; no other code may consume its
  read-to-clear status flags or write charger/expander registers.
- Implement durable atomic `load_inhibit`/`save_inhibit` storage. Missing,
  corrupt or unavailable records must report failure. The session marker is
  written before charging is possible; an unexpected reset/reboot cannot resume
  charging silently. There is deliberately no automatic fault-clear API.
- An audited service procedure must establish the initial record and explicitly
  authorize recovery with CE disabled, after inspecting the pack/fault cause.
  Do not clear the record on every boot. The current core retains an inhibition
  bit, not detailed diagnostic history; add a durable fault-reason log in the HAL.
- Pass `exact_pack_qualified=false` until the actual pack, NTC, connector and
  thermal/current limits have been verified. It prevents charge enable.
- Call `poll` on USB events immediately and periodically within 1000ms, using
  monotonic uint32 millisecond time. `legacy_granted` is true only for a USB
  configuration authorizing 500mA; revoke on detach, reset, suspend or
  deconfiguration. Type-C permission comes from expander P2, not VBUS voltage.
- The state `charging` means charge permission, not measured current or charge
  completion. Decode charging progress separately without stealing status reads.
- On I2C failure, the independent PA0 permission is removed before best-effort
  bus shutdown. Qualify GPIO reset/discharge, independent watchdog and rail
  collapse; ongoing I2C traffic can service the charger
  watchdog, so a latched-fault system must stop other charger transactions.
- The new hardware capture supplies U25/U24 independently of SW19. This core
  still needs a STM32 HAL, target build, host permission lease and qualified
  reset-time hardware charge inhibit before powered-off charging works. Q8/R79 and the PA0
  control path are now routed; see [inhibit review](../../hardware/handset-rev-a/charge-inhibit-review.md).

## Host validation

```
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -fsanitize=undefined \
  firmware/power/tests/charger_test.cpp -o /tmp/handset-charger-test
/tmp/handset-charger-test
python3 scripts/check_handset_charger_policy.py
python3 scripts/check_handset_battery.py
```

Tests cover source loss/return, Type-C versus legacy authorization, delayed
legacy power-good, unchanged steady-state CE, unqualified packs, startup storage
failure, safety timer, open thermistor, eFuse/OCP, register/expander reset,
I2C failure, restart inhibition and polling deadlines including timer wrap.
These are fake-bus host tests; hardware fault injection and STM32/host protocol integration
remain required. LeakSanitizer is unsupported under this environment's ptrace;
validation uses UndefinedBehaviorSanitizer.
