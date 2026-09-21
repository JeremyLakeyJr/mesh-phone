# Pocket enclosure — MakerFocus 3000 mAh

A compact revision for the existing **87 × 154 mm PCB**. The body is
**93 × 160 × 38.8 mm**, with no projecting screw ears: 11 mm narrower at its
widest point and 0.2 mm thinner than the previous enclosure. It is still a chunky
handheld; a phone-width design requires a narrower PCB and repackaged modules.

## Printable files

| File in `exports/` | Purpose |
|---|---|
| `rear.stl` | Beveled rear shell, PCB supports, battery cradle and strap anchors |
| `front.stl` | Front with internal closure columns and locating tongue |
| `port_cover.stl` | Flush expansion-port blank with orientation pin |
| `module_pod.stl` | Detachable external module housing |
| `preview.png` | All four print parts |
| `assembled.png` | Front and rear assembled views, with and without pod |

`enclosure.scad` is the editable source. `part` selects these four parts,
`layout`, `assembly`, `with_module`, or `fit` (translucent fit envelopes).
Run `scripts/export_enclosure.sh` from the repository root to extract current
PCB datums, rebuild every STL, verify closed connected meshes, and render previews.
Requires OpenSCAD and Python with NumPy/Matplotlib; no display server required.

## Battery and interior

Sized for the [MakerFocus 3000 mAh 103665 pack](https://www.makerfocus.com/products/makerfocus-3-7v-3000mah-lithium-rechargeable-battery-1s-3c-lipo-battery-pack-of-4),
listed at **65 × 36 × 10 mm, ±2 mm** (checked September 21, 2026).
The crosswise **67 × 38 × 12 mm** allowance includes that tolerance;
the cradle adds 0.8 mm per side. Its center is [0, -51], below the keypad.
A rounded lip locates the pouch; a soft 8 mm strap threads through the two
side bridges. Do not tighten it enough to compress the pouch. The cradle has
a 14 mm lead exit toward the upper electronics area. Route the lead along the
right interior margin to J13, clear of screws and the module connector.

The PCB underside is 17.3 mm above the rear exterior. The cradle floor is at
3.2 mm, leaving 2.1 mm above the maximum battery allowance for rear keypad
components. Verify solder joints, actual diode heights, strap and insulation
within that space before assembly. The taller rear RF/GPS components occupy
the upper region instead of being stacked above the battery.

MakerFocus offers 1.25 and 2.0 mm connector options. Confirm the purchased
plug and polarity against J13; this enclosure update does not change the PCB
connector or resolve the existing power-path design blockers.

## External module port

A **24 × 14 mm radiused opening** is centered on J16 at [-3, -10]. The
**68 × 44 mm recessed interface** has a 0.3 mm fit allowance, two M2 fasteners
58 mm apart, and an asymmetric locator. The blank fills the recess when no
module is fitted. Screw heads may sit slightly proud; no exterior ears remain.

The removable pod shares this interface and adds **16.8 mm** of rear depth
only while installed. Its outer envelope is 68 × 44 × 18 mm. Internal walls
leave 63.2 × 39.2 × 15.6 mm before screw pillars and strap bridges. A conservative
central module allowance is **48 × 26 × 10 mm**, with extra room elsewhere for
cable routing. Use foam and a soft strap through the internal anchors; alter the
parametric pod for larger modules. It does not claim to fit every RF/NFC/LTE
carrier. The LTE carrier remains part of the host's provisional front stack.

Plug a short keyed JST-GH cable into J16 through the opening, then secure the
pod; this is a cable-connected module, not a blind-mate electrical card slot.
The shell and screws carry module loads, not J16. Keep the cable within the
50 mm target from [the interface contract](../../hardware/rev-f/INTERFACES.md).
The existing electrical contract requires power off and USB disconnected for
module swaps. Antenna windows and any external module connectors must be
added for the selected module; the generic pod is otherwise closed.

## Closure, durability and assembly

Walls/faces are 2.4 mm; small corner radii preserve clearance around the square
PCB. A 1 mm edge bevel softens the pocket-contact edges. A perimeter tongue
aligns the halves. Four recessed M2 screw heads align with H1–H4, passing through
the front columns and PCB mounting holes into 1.7 mm rear pilot holes. This
uses the board's existing mounting datums without side projections.

Start with approximately 28 mm under-head-length M2 screws for the main body,
then measure engagement; target 6–8 mm without bottoming the 9 mm pilots.
Do not over-tighten against the PCB. Dock mounting uses M2 nuts inserted into
4.8 mm corner-to-corner hex pockets from inside before fitting the board.
Use approximately 6 mm screws for the blank and 22 mm for the pod, confirming
actual nut engagement and head profiles on a fit print. Nut pockets and ports
are not sealed; no water/dust/drop rating is claimed.

Print each part exterior-side down. The exports are already oriented this way.
The 9–10 mm strap-slot bridges and side openings may need local support/tuning.
Inspect layer adhesion and fit before installing electronics. No physical
durability or drop test has been performed.

## Remaining measured-fit work

The documented display outline is 61 × 92.44 mm; four front tabs locate it at
[0, 30]. The opening is 50 × 76 mm and its surrounding ledge accepts thin foam
tape. Confirm the visible display area, FPC fold and actual panel thickness.
The trackball opening remains at [-4.5, -23]; its 25 × 22 × 11 mm carrier needs
measured retention and must clear nearby controls. Keycaps/plungers are not
included. Front clearance is 17.5 mm: 12.44 mm for the documented LTE carrier,
4 mm provisional display thickness, and 1.06 mm assembly clearance. Confirm
header seating and actual display/trackball heights. Increasing `front_clearance` increases thickness.
USB access must be checked with the actual recessed socket and cable overmold.
These are mechanical prototypes, not a verified populated-hardware fit.

## Geometric verification

All four exported parts pass closed-edge and single-connected-component checks.
OpenSCAD intersection checks in `check_fit.scad` found no solid overlap for the
case halves, rear/blank, rear/pod, or rear/battery allowance. The pod test offsets
its seating plane by 0.001 mm to exclude coincident-surface artifacts. These
checks do not include unmodeled populated components or prove physical fit.
