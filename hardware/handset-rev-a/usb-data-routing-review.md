# USB data routing — 2026-10-07

USB-C data now connects through U17 protection and R88/R89 termination to the
ESP32-S3. Both cable orientations pass physical continuity, polarity, planar
length and reference-copper checks. Native DRC and schematic parity remain zero;
remaining unconnected items fall from 285 to 279. This is a completed CAD routing
step. USB electrical qualification and fabrication release remain open.

## Circuit and placement

| Signal | Connector contacts | U17 external pass-through | Series resistor | ESP32 module |
|---|---|---|---|---|
| D− | A7, B7 | 10 ↔ 1 | R88, 22 Ω | U1.13 / GPIO19 |
| D+ | A6, B6 | 9 ↔ 2 | R89, 22 Ω | U1.14 / GPIO20 |

The TI protection channels are used with the polarity shown above; the pin names
D1+/D1− in its symbol do not change the table's actual net assignments. Pins 9/10
are **not internally connected** to 2/1: explicit PCB traces join them. NC lands
6/7 remain unused. TI documents external flow-through routing in its
[TPDxE05U06 datasheet, layout section](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf).

R88/R89 are [Yageo RC0402FR-0722RL](https://www.yageogroup.com/component-documentation/download/specsheet/RC0402FR-0722RL),
22 Ω, 1%, 0402. This is an initial termination value, following
[Espressif's USB schematic guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html#usb).
Their board-side paths to the module pads are each 6.03 mm. No shunt capacitors
are populated or claimed as qualified; evaluate whether tuning footprints are
needed during the remaining signal-integrity review. All existing footprint
positions, connector holes and land geometry are preserved.

## Stackup and routing evidence

The selected **design target** is JLCPCB JLC04161H-7628, nominal 1.6 mm, four
layers: 35 µm outer copper, 15.2 µm inner copper, 0.2104 mm 7628 outer dielectrics,
and a 1.065 mm core. These published rounded copper/dielectric dimensions total
1.5862 mm; the nominal board setting stays 1.6 mm. The manufacturer must confirm
finished thickness and tolerances. This is not an approved order or fabrication
stackup. [Published stackup and material inputs](https://jlcpcb.com/impedance).

Native KiCad stackup data and the `USB data` net class record the target. The
uniform paired trunk uses 0.29 mm width and 0.21 mm edge spacing. The local
finite-volume quasi-TEM screening gives 89.55 Ω at a 5 µm grid and 89.83 Ω at a
2.5 µm grid. The 0.28 Ω refinement difference checks numerical sensitivity; it
does not validate the material model. The model excludes pad/via discontinuities,
uncoupled tuning, etch tolerances, glass weave and module internals. Obtain a
fabricator field-solver result and impedance coupon for the 90 Ω ±10% target.
See [the input/output record](generated/usb-impedance-estimate.json) and
[the reproducible estimator](../../scripts/estimate_handset_usb_impedance.py).

Both orientations have approximately 42.638 mm of planar connector-to-module
copper, excluding resistor bodies, via barrels and module-internal routing.
Nominal CAD mismatch is under 0.01 mm; the check limit is 0.25 mm. Symmetric
connector branches give the same path lengths in either cable orientation.
There are three through-via transitions per leg. The route includes uncoupled
fanout and length tuning, so the uniform-trunk estimate is **not** a claim that
the entire path has controlled impedance. Review those sections and validate USB
electrical behavior before closing the USB engineering blocker.

Ground pours on In1/In2 provide the adjacent reference for the outer signal
layers. The checker samples the trace center and both edges plus a 0.10 mm
margin, at intervals no larger than 0.10 mm. All 2,928 samples pass outside
recorded local antipad exemptions within 0.65 mm of a signal via. Six added
return vias are independently checked for connection to board ground; each
signal transition has at least two connected ground vias within 2.5 mm.
This is a geometric return-path check, not an ESD or high-frequency measurement.
The design targets follow [Espressif's USB layout guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html#usb).

## Power preservation and validation

Two existing VBUS segments were changed to make room for the connector data
fanout. The local bridge now uses In1 with a new through via at (128.5, 56) mm;
its route avoids the front USB reference corridor. All other 7,858 original
track/via items are preserved exactly. The new inner-layer power copper needs
current/voltage-drop and thermal review against the selected 15.2 µm copper;
continuity alone does not qualify it. All 118 existing local power-entry pad
connections still pass. No clearance rule was relaxed and no exclusion added.

Seven regression cases cover the installed board, a removed external ESD
bridge, swapped host polarity, missing reference fill, missing transition
return, wrong termination, and added skew with continuity retained. The full
project check also verifies previous power, display, backlight, expansion and
radio-power work. The release gate independently reruns the USB geometry checks.

- [Actual copper/path/reference report](generated/usb-data-check.json)
- [Regression results](generated/usb-data-tests.json)
- [Change manifest](generated/usb-data-update.json) and [added-parts BOM](generated/usb-data-bom.csv)
- [Pre-change source archive](../../archive/handset-before-usb-data/2cb4ad59cd64)

The saved checkpoint has 261 components, 2,537 passing integrity assertions,
zero DRC/parity findings, 30 ERC findings and 279 unconnected items. All eleven
engineering blocker groups stay open. Still obtain USB footprint/stackup DFM,
qualify protection placement and ground returns, source current and VBUS copper,
termination and USB eye behavior, and finish the rest of the board. No fabrication
or power-up release is granted by this routing change.
