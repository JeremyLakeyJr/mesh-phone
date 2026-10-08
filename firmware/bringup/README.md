# ESP32-S3 keypad bring-up application

Cross-built with ESP-IDF v5.4.2 for the handset's ESP32-S3-WROOM-1-N16R8.
This application provides I²C keypad scanning, GPIO interrupts, USB event logs
and explicit start/stop/recovery commands. It has **not been flashed or tested
on hardware**. The incomplete PCB remains blocked for fabrication and power-up.

## Build and evidence

Install [ESP-IDF v5.4.2](https://docs.espressif.com/projects/esp-idf/en/v5.4.2/esp32s3/get-started/linux-macos-setup.html)
and its ESP32-S3 tools. The build script checks SDK commit
`f5c3654a1c2d2a01f7f67def7a0dc48e691f63c0`.

```sh
. /path/to/esp-idf/export.sh
bash firmware/bringup/build.sh /tmp/handset-esp32-bringup
python scripts/check_handset_bringup.py
python scripts/check_handset_keypad_firmware.py
```

Outputs include `handset_keypad_bringup.bin`, its ELF, bootloader, partition
table and `flasher_args.json`. Use the complete generated flash layout after
hardware commissioning approval; the application binary alone is not a full
flash image. This build does not flash a device or alter eFuses.

The configuration uses 16 MB flash, DIO at 40 MHz, internal RAM and no sleep.
PSRAM is unused. SDK/bootloader console logs are disabled; the application owns
the USB Serial/JTAG driver. UART console output is not configured. ROM behavior
before this application starts is outside its control.

`validation/build-report.json` records the SDK/compiler, source hashes,
image hashes, image target, flash size and build configuration checks.
`validation/python-packages.txt` records the Python build environment.
`validation/host-tests.json` records session/command tests and the GPIO contract.
The tests reject the formerly documented but incorrect GPIO18 IRQ mapping.

## Wiring and ownership

| Function | ESP32 GPIO | Module pad |
| --- | --- | --- |
| SDA | 10 | U1.18 |
| SCL | 9 | U1.17 |
| Keypad IRQ | 8 | U1.12 |
| USB D− / D+ | 19 / 20 | U1.13 / U1.14 |

The GPIO contract is checked against the native schematic and connectivity
manifest. Only U2 at I²C address 0x34 is accessed, at 100 kHz using R3/R4 external
pull-ups. Transfers have 20 ms timeouts. The scanner task owns the synchronous
[I²C master driver](https://docs.espressif.com/projects/esp-idf/en/v5.4.2/esp32s3/api-reference/peripherals/i2c.html).
The IRQ handler only wakes that task. Polling every 10 ms covers a missed edge;
a still-low IRQ schedules another batch with a mandatory scheduler yield.
Each driver call reads at most ten events. Poll/service timing needs measurement
on the assembled board; these settings are not a throughput guarantee.

No radio, modem, display, media, charger, expansion or backlight enable is
commanded. U2 GPIO direction/output registers remain untouched. The application
does not replace the STM32 power supervisor or the future full handset firmware.
It does not reset shared MCU_EN automatically.

## USB commissioning interface

After the hardware is approved, powered correctly and the full image programmed,
connect its [native USB Serial/JTAG port](https://docs.espressif.com/projects/esp-idf/en/v5.4.2/esp32s3/api-guides/usb-serial-jtag-console.html).
Use the SDK Python environment, which includes pyserial:

```sh
python firmware/bringup/monitor.py /dev/ttyACM0
```

The monitor does not toggle DTR/RTS intentionally, flash the board or start
scanning automatically. Port naming is host-dependent. Send LF-terminated
commands (CRLF also works):

- `status`: report active/valid state, held-key bitmap, IRQ level and log drops.
- `start`: with **all keys released**, initialize U2 and begin scanning. A second
  start during an active session is rejected so it cannot silently flush keys.
- `stop`: stop host scanning, disable its IRQ and invalidate held-key state.
  This does not assert hardware reset or guarantee that U2 stops its own scan.

Each event identifies SW1–SW16, zero-based row/column and PRESS/RELEASE.
Held-mask bit zero is SW1; bit fifteen is SW16. Status repeats once a second,
including while idle. Fault values are 0 ready, 1 reset/configuration required,
2 FIFO overflow, 3 invalid event, and 4 transfer error. On a fault, host scanning
stops and the held-key state becomes invalid. Release all keys, resolve the
cause, then explicitly start again. Setup failures require reset/reboot.

USB runs in a separate task with bounded queues and nonblocking writes. A slow
or disconnected host can lose records without blocking scanning. Sequence gaps
and `queue_drop` / `usb_drop` counters expose losses; a partial record is followed
by a new line. `usb_drop` also counts rejected commands when its queue is full.
Discard incomplete records and treat gaps as lost diagnostic evidence. This is
not a lossless event recorder or UI action pipeline.

Commission one switch at a time first. Verify every press/release, a held key,
stop/start, USB disconnect/reconnect, absent U2, reset and FIFO overflow. The
matrix has no per-key diodes; arbitrary multi-key rollover is not established.
Mechanical fit, IRQ timing, debounce, electrical noise and USB signal integrity
still need bench qualification.
