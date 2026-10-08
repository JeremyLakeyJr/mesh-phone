# Keypad commissioning driver

Portable C++17 `controller.hpp` controls the handset's U2 keypad scanner at
7-bit I²C address 0x34. The [ESP32 bring-up application](../bringup/README.md) now integrates it with
I²C, GPIO8 interrupts and USB logging and has been cross-built for ESP32-S3.
No image has been flashed or tested on the physical handset.

Implement `keypad::Bus` using serialized, bounded I²C transfers. Give this driver
exclusive ownership of U2's scan/configuration/FIFO registers. Call
`initialize()` with all keys released after hardware commissioning approval.
A GPIO8 falling-edge ISR should wake a task; perform I²C work in that task,
not the ISR. Poll periodically as well as on IRQ, drain while IRQ stays low,
and bound the task's work per scheduling interval. Determine the actual service
rate by measurement; each call returns at most ten events.

Initialization configures only the four matrix rows/columns for scanning,
enables their pull-ups/debounce, disables GPIO FIFO events, and verifies writes.
GPIO direction and output-latch registers are untouched. It neither initializes
nor enables display, backlight, media, modem or RFID outputs. A future shared
U2 controller must integrate those GPIO functions with this register ownership;
do not run independent configuration writers against the chip.

`Batch` contains zero-based row/column press/release events. The physical switch
number is `4 * row + column + 1` (SW1–SW16). Key legends and UI actions are not
assigned here. Process events only when status is `ready`. Any other status
invalidates the application's entire held-key state; cancel gestures/actions,
report the fault and require explicit recovery with all keys released. A failed
or overflowed drain publishes no partial batch. The driver never asserts the
shared MCU_EN reset net automatically.

The implementation follows the [TI TCA8418 datasheet, revision G](https://www.ti.com/lit/ds/symlink/tca8418.pdf),
including the overflow and false-CAD errata. FIFO data loss latches a fault;
CAD status is never interpreted as a reset command. Matrix ghosting remains
possible without per-key diodes: commission one key at a time, and qualify
required multi-key combinations separately. This driver does not promise
arbitrary-key rollover or filter phantom presses.

Run the host checks:

```sh
python scripts/check_handset_keypad_firmware.py
```

Tests cover all 16 press/release codes, initialization and GPIO-register
preservation, FIFO order, empty polls, overflow before/during draining,
invalid events, configuration loss, arrival during interrupt acknowledgement,
ignored writes and transfer failure at each initialization/poll operation.
`test-report.json` binds the result to the tested source hashes.
