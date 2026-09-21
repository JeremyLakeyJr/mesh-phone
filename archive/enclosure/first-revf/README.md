# Rev F enclosure prototype

The replacement uses the active PCB's **87 × 154 mm** outline, four mounting
holes and sixteen switch positions. The old enclosure assumed a 70 mm board
and has been retained in `../../archive/enclosure/`.

- `enclosure.scad`: editable source; `part` selects layout, rear, front or assembly.
- `pcb_geometry.scad`: generated board datums; coordinates are centered and KiCad Y is inverted.
- `exports/rear.stl`, `exports/front.stl`: separate parts oriented for printing.
- `exports/preview.png`: print-layout preview.

The body is 93 × 160 × 39 mm assembled, plus four external screw ears (104 mm
maximum width). Walls and face are 2.4 mm. PCB underside is 20 mm above the
outside rear floor. M2 self-tapping screws use 1.7 mm pilots; lid clearance holes
are 2.3 mm. Select screw lengths for 6–8 mm engagement without bottoming out.
PCB supports match H1–H4; separate external ears retain the removable front.
The locating lips face inward when assembled.

USB and power access are on the right side at the actual USB1/SW1 Y coordinates.
A rear opening follows J16 with two M2 through-holes for a future cable-retention
plate. It is cable access, not a completed docking mechanism. Internal SD/SIM
access requires removing the cover.

## Measurements still needed before a final print

The PCB defines connector positions, not the attached display, trackball, camera,
module heights or button cap geometry. The 50 × 76 mm display opening centered
at [0, 33], trackball center [-4.5, -23], 15 mm front clearance, port heights and
38 × 54 × 12 mm battery allowance are adjustable prototype assumptions.
Display and trackball need a measured carrier/retention solution; the sixteen
key holes require caps/plungers reaching the front panel. No camera aperture is
invented from its connector location.

Check populated-board clearances, especially rear radio/GPS parts and battery
leads. Battery position is proposed at [0, 43] under the PCB, held with removable
foam/strap retention (not supplied). Verify its thickness against rear components;
no battery clamping feature is included. Check the USB plug reaches the recessed
receptacle. Measure switch travel and expansion cable latch access. Antenna
placement is not validated by this model.

Print the front face down and rear floor down. Use a short fit print first for
screw pilots, mounting bosses and ports. Side openings may need bridging/support
according to the printer. STLs are geometric prototypes, not a verified fit to
assembled hardware.

Rebuild from repository root with `scripts/export_enclosure.sh` (Python 3 with NumPy/Matplotlib and
OpenSCAD required). Source uses no downloaded CAD dependencies.
