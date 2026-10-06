# Expansion power control and signal isolation — 2026-10-05

The expansion update replaces U14's permanently enabled supply and direct
host signal connections with separately controlled power and signal isolation.
This is an engineering implementation, not fabrication or power-up approval.

## Ground-return revision — 2026-10-05

Local GND pours on In1.Cu and In2.Cu fill previously uncovered areas above
the trackball cutout. Their outlines subtract existing pours, preserving
existing zone geometry and avoiding isolated overlap fragments. Ninety
expansion-added inner-layer ground segments (36.237 mm total) are removed.
Four short B.Cu ground segments (3.985 mm total) reinforce the ESD escapes
and directly join U16 ground pads 3/8. Three segments are 0.30 mm wide; the
U16.3 escape is 0.18 mm to retain clearance from the IRQ via.

All signal routing, all footprint positions and 7,856 retained copper items
are unchanged, including all 4,183 pre-expansion copper items. The final board
has 7,860 copper items. The previous board and reports are in
[`archive/handset-before-expansion-ground/a952add783fb`](../../archive/handset-before-expansion-ground/a952add783fb).
The current geometry/hash and removed segment IDs are recorded in
[generated/expansion-ground-update.json](generated/expansion-ground-update.json).

The [In1 ground preview](generated/previews/expansion-ground-In1.svg) and
[In2 ground preview](generated/previews/expansion-ground-In2.svg) show the
updated fill and remaining signal clearances.

Both ground-return tests and all six expansion regression tests pass. Removing
the new pours in a test copy breaks ESD ground continuity, demonstrating that
the new return does not rely on the removed detours. All previous copper checks
pass. Native DRC retains only the four USB1 hole-clearance findings, with 285
unconnected items and zero schematic parity findings.

This is a geometric/DC improvement, not ESD qualification. TI recommends
short, low-impedance ground returns and protection close to the connector
([TPD4E05U06 datasheet, layout section](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf)).
U15 connector distance, remaining signal-created plane slots, current
spreading and transient clamping still require review and measurement. No
new vias are added; the existing J16.8/U14.1/U14.6/U16.1 filled-and-capped
via-in-pad requirements remain open with the assembler.

## Circuit and evidence

U33, TCA9537DGSR, shares the host I2C bus at fixed 7-bit address 0x49.
P0 controls TPS2553 EN, P1 reads its active-low fault, P2 arms the signal path,
and P3 remains an unused input. R83/R84 (4.7 kΩ) pull the two permissions low
when U33 resets to inputs. RESET follows MCU_EN; INT is unused. The routing scope also includes the
existing R1/C1 host reset network and checks the R3/R4 I2C pull-ups. The remaining
ESP32 boot-strap and PSRAM pins are unchanged. C91 provides local bypass.
The [TI TCA9537 datasheet](https://www.ti.com/lit/ds/symlink/tca9537.pdf)
supports the pin map, reset behavior, fixed address and register sequence.
TI names DGS VSSOP; the corresponding KiCad land pattern is
`MSOP-10_3x3mm_P0.5mm`. Independently verify the selected package before release.

U34, SN74CB3Q3245PWR, interrupts all seven accessory signals before the
existing 33 Ω series resistors and port-side ESD arrays. Its eighth channel
is grounded on both sides; pin 1 is NC. C92 bypasses its supply. This is a
bidirectional bus switch, not a voltage translator. Compatible 3.3 V accessories
remain mandatory. The [TI bus-switch datasheet](https://www.ti.com/lit/ds/symlink/sn74cb3q3245.pdf)
specifies disabled isolation, powered-off leakage and supply current; the
[TI switch databook](https://www.ti.com/lit/ug/scdd003a/scdd003a.pdf) includes
the package pinout. Leakage is finite, so disconnected does not mean zero
current or immunity to externally powered accessories.

U35, SN74HCS10PWR, drives `/OE = NOT (power_EN AND IO_ARM AND FAULT_N)`.
A real Schmitt-input NAND accommodates the open-drain fault signal; C93 is
its bypass capacitor. Unused gate inputs are grounded and outputs are NC.
R42 changes from 100 kΩ to 10 kΩ for the fault pull-up; R86 pulls /OE high
through 220 kΩ. At a 3.6 V supply, R86 plus the switch's specified input leakage
keeps the static sink load within the NAND's 20 µA low-voltage output test
condition. This calculation does not qualify transition timing or thresholds
through ramp/brownout. See the [TI SN74HCS10 datasheet](https://www.ti.com/lit/ds/symlink/sn74hcs10.pdf).

R41 remains 100 kΩ ±1%. The [TI TPS2553 datasheet](https://www.ti.com/lit/ds/symlink/tps2553.pdf)
yields a calculated current-limit range of approximately 232–306 mA including
resistor tolerance. This is neither an accessory current allocation nor proof
of adequate host supply margin. R87 (10 kΩ) bleeds EXP_3V3; accessory capacitance
and external power remain unknown, so no universal discharge interval is claimed.
Orderable parts are recorded in `generated/expansion-bom.csv` and native CAD.

## Reset, faults and firmware

An external MCU_EN reset makes the permission pins inputs and lets the
pull-downs turn the port off. An ESP32 internal software/watchdog reset need
not assert MCU_EN. A module holding the shared I2C bus low can prevent U33
shutdown commands; recovery then requires external reset or handset power-off.
Do not claim software-independent latched shutdown from this topology.

The NAND disconnects signals while FAULT is asserted, after the TPS2553's
fault-reporting delay. It reconnects if FAULT clears while both permissions
remain high. Brief faults can escape polling. There is no rail-good detector,
no independent watchdog on these permissions, and no hot-swap qualification.
Exchange modules only with the handset powered off. Reserve address 0x49 and
qualify every accessory's address, signal timing, chip-select and idle behavior.

The [portable controller](../../firmware/expansion/README.md) preloads output
0xF0 before direction 0xFA, verifies writes, enables supply with 0xF1, then arms
signals with 0xF5 only after an explicitly qualified settling interval.
Observed faults and missed polling deadlines latch software inhibition.
Failed bus operations produce an unknown/reset-required state even after a
best-effort OFF write. It is a host-tested core, not an integrated target build.

## Remaining qualification

Measure startup/inrush, load/current-limit tolerance, output discharge, power
ramps and brownout, external-reset behavior, fault delays/reconnection, stuck
bus recovery, isolation leakage, SPI edges and I2C capacitance. Audit bus-switch
charge-pump current and dynamic gate/controller demand in the system budget.
Verify routing widths, voltage drop, return paths, bypass loops, package land
patterns and assembly clearance against the final stackup and enclosure.
The total accessory and control load remains unqualified in the power inventory.

## Validation and preservation

The installed revision has 259 components and passes all 2,525 integrity
assertions, with zero parity or placement findings. Native ERC retains 30
findings; DRC retains only the four existing USB1 hole-clearance findings.
Unconnected items decrease from 327 to 285. All 31 expansion continuity
groups pass, along with six expansion regression tests, seven backlight
tests, five display tests and the previous power-distribution continuity
checks. The C++17 controller host tests pass with strict warnings and UBSan.

All 4,183 original copper items are preserved; 3,763 copper items are added.
The prior generated project is archived at
[`archive/handset-before-expansion/c7150cd5a277`](../../archive/handset-before-expansion/c7150cd5a277).
Routing records describe construction history; the final native board and
independent continuity/DRC reports establish the installed geometry.
Existing routed copper remains unchanged. U15 moves from (89, 75) to
(84, 76) mm to obtain clear signal escapes. Its longer path to J16 must be
qualified for ESD/surge behavior; continuity alone does not establish adequate
clamping at the protected pins, and protection layout may need further revision.
The preparation script refuses this move if U15 is already routed. U15 and
J16 references move to the assembly layer to clear the crowded connector
silkscreen. Other retained component placements remain unchanged, including U16.
The router permits connector/ESD escapes in a bay above the native y=80 mm
trackball cut, maintaining the native 0.5 mm copper-to-edge rule with extra grid margin
(trace centerline limited by its width, via centers at or above y=79.24 mm); native DRC
checks the actual cut clearance. Final module/body fit still needs review.

J16.8, U14 power lands 1/6 and U16.1 use 0.5 mm vias with 0.3 mm drills in
their solder lands because surrounding copper blocks conventional escapes. This requires filled-and-capped via-in-pad
processing and independent component assembly review; an ordinary open via
is not an approved substitution. Escape routes and power branches still need
signal-integrity, current-capacity and return-path review against the stackup.
MCU_EN and some accessory nets use local In1.Cu bridges through otherwise
enclosed areas. Their measured lengths are recorded in the routing manifest. Ground
fill clears these traces; physical ground continuity and high-frequency return
quality are different checks. The latter remains an independent layout review.

The initial routing included a roughly 53 mm ESD ground construction route.
The ground-return revision above removes its inner-layer detours and adds
local pours and a direct U16 ground bridge. DC continuity still does not
establish effective surge return impedance; ESD protection and remaining
plane slots require independent qualification before release.

The full `scripts/check_handset_pcb.sh` check passes and regenerates the
schematic PDF and board/assembly previews. System-power and display/expansion
budget suites pass five and six tests respectively. The release gate still
rejects fabrication with all eleven engineering blocker groups open; it
reports no integrity, parity, expansion, backlight or display continuity failures.
