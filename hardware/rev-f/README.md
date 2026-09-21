# Owasso1 Rev F — engineering checkpoint, not a fabrication release

Open `mesh-phone.kicad_pro` in this directory. The project in `../main/` is
the preserved original, not this corrected revision.

Implemented in schematic and PCB:

- MAX-M10S GPS with passive-antenna U.FL, UART, PPS and bypass capacitors.
- Rear keyed 10-pin JST-GH expansion interface, with a current-limited 3.3 V
  supply and shared SPI/I²C. Switch off and disconnect USB before swapping.
- MCU EN/BOOT support, usable SPI pin assignments, keypad expander pin-order
  corrections, display controls and I²C pull-ups.
- Removal of the switch connection that directly joined USB 5 V to the battery.
- Reconciled schematic/PCB pad contracts, with original component placements
  preserved. New parts are rear-mounted.

Read [INTERFACES.md](INTERFACES.md) before designing a module. This is a keyed
cable connector, not a finished blind-mate mechanical docking system.

## Not safe to order or power yet

The inherited battery protection, charger/power path, 3.3 V regulator and 5 V
boost circuits still require redesign. The A7670E modem/carrier is not approved
for the US target. Remaining radio-control, IR, fuel-gauge, RFID and SIM
interfaces are incomplete. See the full
[connection review](../../docs/reviews/review-2026-09-20/CONNECTION_REVIEW.md).

RF/USB impedance and antenna/enclosure placement are unverified. Ground vias
at the new reset circuitry overlap solderable pads; move them outside pads or
specify a suitable filled/capped via process during the final DFM pass. Do not
assume ordinary open vias in solder pads are assembly-ready.

## Verification evidence

Latest checkpoint: **608/608 contract and placement checks passed**. Native
KiCad DRC reports **0 errors, 0 unconnected items and 0 schematic-parity
findings**, with 5 footprint-library mismatch warnings. ERC still reports
**2 errors and 24 warnings** from unresolved supply modelling and interfaces.
The five footprint warnings concern J10, USB1, U1, J14 and J3; their modified
pad/geometry contracts need final library and manufacturer-drawing review.

- `verification-summary.json`: independent net/placement checks, native tool
  counts and SHA-256 fingerprints of the checked files.
- `drc-final.json`: native KiCad DRC, including schematic parity.
- `erc.json`: unresolved electrical-rule findings, not waived with power flags.
- `owasso1-engineering.pdf`: two-sheet schematic for review.
- `previews/`: schematic SVGs.

Zero routing errors would not certify circuit operation. Firmware, bench
bring-up, battery-safety verification, RF tests and cellular carrier acceptance
are still required. No revised manufacturing package has been released.

To repeat the read-only contract checks, run `python scripts/verify_revF.py` from the
repository root after exporting a fresh `netlist.xml`. The build/routing and
layout experiment scripts in `../../archive/scripts/` are checkpoint tools, not an
idempotent pipeline: do not replay them on this finished checkpoint.
