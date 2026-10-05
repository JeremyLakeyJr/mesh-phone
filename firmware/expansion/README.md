# Expansion controller core

`controller.hpp` is portable C++17 logic for U33 (TCA9537 at 7-bit address
0x49). It is not installed ESP32 firmware and does not authorize powering the
incomplete board. See the [circuit review](../../hardware/handset-rev-a/expansion-control-review.md).

Initialization writes and reads back output latch 0xF0, polarity 0x00 and
configuration 0xFA, in that order. P0 and P2 become outputs only after the
OFF latch is verified; P1 is fault input and P3 stays unused. Enabling requires
explicit load/startup and bus/address qualification plus a measured settling
interval. Power-only 0xF1 precedes signal-arm 0xF5. Polling verifies configuration,
output levels and FAULT every 100 ms or faster, including during settling.
This interval is a software deadline, not an electrical protection guarantee.
A detected fault or late poll latches OFF until an explicit initialization.
Repeated polling never rewrites the ON latch.

The hardware NAND disconnects signals while FAULT is low, after the TPS2553's
fault-reporting delay. It does **not latch short faults**: the signals may
reconnect when FAULT clears before software observes it. TPS2553 current limiting
is automatic; a polling-only driver can miss brief faults. Short-circuit/startup
and fault persistence must be qualified; there is no claim of latched hardware
shutdown or a rail-good measurement.

Integration must provide bounded-time, serialized I2C operations. Reserve
0x49, prevent other owners from writing U33, and validate the accessory against
all host I2C addresses and shared-SPI behavior. Configure host chip selects
inactive before arming. Never enable unknown or externally powered modules.
The bus switch does not translate voltage; accessories must use compatible
3.3 V signaling. Swap modules only with handset power off.

A failed transfer triggers a best-effort OFF write and reports
`unknown_reset_required`, even if a later write succeeds. A stuck accessory can
hold the same I2C bus used to control U33. Recovery requires an external
MCU_EN reset or whole-handset power cycle, followed by explicit initialization
and qualification. An ESP32 software/watchdog reset alone need not assert
MCU_EN. OFF means verified enable outputs low, not measured zero accessory
voltage; R87 is a bleed resistor, not an instant discharge guarantee. The target
must also detect missed execution externally: software cannot enforce its
poll deadline if it stops running.

Run host tests:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -fsanitize=undefined \
  firmware/expansion/tests/controller_test.cpp -o /tmp/handset-expansion-test
/tmp/handset-expansion-test
```

The fake bus covers initialization order, unqualified requests, delayed arming,
fault inhibition, steady-state traffic, missed deadlines, timer wrap,
expander reset, ignored writes, failed transactions and stuck-bus shutdown.
A target build, HAL integration, hardware fault injection and measured timing,
leakage, current, reset behavior and thermal limits remain open.
