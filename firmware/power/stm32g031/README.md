# STM32G031 supervisor commissioning target

A real, cross-linked Cortex-M0+ target for U25 STM32G031G8U6 is now present.
**This is an inhibited diagnostic image, not operational charging firmware.**
It has not been flashed or run on hardware. The PCB remains unreleased.

Build from the repository root using Clang/LLD and LLVM binary tools:

```sh
bash firmware/power/stm32g031/build.sh
```

Outputs default to `/tmp/handset-stm32g031`: `supervisor.elf`, `supervisor.bin`,
`supervisor.map` and `build-report.json`. An optional argument selects another
output directory. There is no automatic flash/download action or build-time
network dependency. Pinned ST/Arm headers and licenses are included in `vendor/`;
`vendor-manifest.json` records provenance and content hashes.

## Implemented

- Cortex-M0+ reset vector, data/BSS initialization, default fault handler and
  1 ms SysTick. Explicit HSI16 system/peripheral clock selection.
- Linker limits for 64 KiB flash and 8 KiB RAM. Application uses at most 60 KiB;
  two 2 KiB pages are reserved for a future journal. At least 1 KiB is reserved
  above static RAM for the stack. This is not a measured stack-use guarantee.
- PA0 is preloaded low before output mode. Every arm request drives it low;
  requesting high returns failure. The main loop also holds it low.
- Private I2C1 on PB8/PB7 AF6. Register writes and repeated-start byte reads
  have a shared 25 ms transaction deadline and a finite spin fallback. Errors
  drop PA0 before peripheral reset. No automatic stuck-bus recovery/rearming.
- Conservative Standard-mode timing at PCLK 16 MHz: prescaler 250 ns, low/high
  counts 10/8 us before filter/synchronizer delays. Actual frequency and rise
  times must be measured; this is not a validated 100 kHz timing profile.
- PA11/PA12 remapping and AF6 for I2C2 at 7-bit address 0x42. No internal
  pull-ups on the TCA9800 B side. Read-only, polled diagnostic slave with clock
  stretching; writes are discarded and cannot grant power permission.
- Independent watchdog, nominal ~1 s at 32 kHz LSI, refreshed only by the
  foreground loop. Actual bounds require LSI tolerance and hardware testing.
  Fault handlers stop refreshing. Reset cause and option bytes are observable;
  firmware does not write option bytes, configure BOR or erase/program flash.
- The portable charger core is compiled into the ARM image. Startup calls
  `begin(..., false)`. Missing durable storage deliberately reports failure;
  the core requests CE/legacy shutdown and remains fault-inhibited. It does
  not repeatedly service charger registers after that fault.

`load_inhibit` and `save_inhibit` **are deliberately unavailable**, returning
failure rather than inventing a valid persistent record. Thus this image cannot
be turned into working charging firmware by changing the pack-qualified flag.

## Diagnostic interface

Read eight consecutive bytes directly from I2C address 0x42; no register-address
write is needed. Data is snapshotted at address match. Extra bytes read as FF.

| Byte | Meaning |
| --- | --- |
| 0 | Diagnostic format version: 1 |
| 1 | Charging forcibly inhibited: 1 |
| 2 | Portable controller state enum; startup is expected to report fault |
| 3 | I2C1 error counter, low eight bits |
| 4–7 | Captured RCC reset-cause register, little endian |

`supervisor_diagnostics` is also available through SWD, including raw option
bytes and loop/error counters. The slave is polled once per foreground iteration
and can stretch SCL while waiting for SysTick. Validate ESP32 timeout settings.
This diagnostic format is not the future charging-permission protocol; it has
no grant, clear-fault, rearm, passthrough or flash-write commands.

## Validation and next work

The actual ELF passes architecture/EABI, vector-table/Thumb entry, load-region,
flash journal boundary, static RAM/stack reserve and unresolved-symbol checks.
The commissioning build is 2,336 bytes flash and 44 bytes static RAM with the
recorded compiler. Portable charger tests pass with strict warnings and UBSan.
These checks do not execute ARM peripheral behavior or measure hardware timing.

Next implement a power-loss-safe durable inhibit/fault journal, audited service
initialization/rearm, the host protocol with expiring legacy-USB permission and
ESP32 integration. Complete BOR/reset/watchdog provisioning and target-level
fault-injection tests before permitting any charging. Keep exact-pack
qualification false until pack, thermistor, connector and current limits are
verified. Validate bus transactions, clock stretching, reset shutdown and
unpowered-host isolation on the qualified hardware revision.

Register definitions come from [ST's CMSIS device package](https://github.com/STMicroelectronics/cmsis-device-g0)
and [Arm CMSIS 5.9.0](https://github.com/ARM-software/CMSIS_5/tree/5.9.0).
Clock, GPIO remapping and I2C behavior follow
[ST RM0444](https://www.st.com/resource/en/reference_manual/rm0444-stm32g0x1-advanced-armbased-32bit-mcus-stmicroelectronics.pdf);
board pin assignments remain in `power-supervisor.kicad_sch`.
