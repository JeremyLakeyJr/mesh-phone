# MESH-PHONE handset concept

A new industrial design based on the user's MAKERphone 2.0 reference: a narrow
clipped-corner frame, smaller upper screen, centered trackball, rectangular
4×4 keypad, dark recessed face and shallow side grip channels.

**This requires a new PCB, a smaller touchscreen, and revised harnesses. It does
not fit the existing Rev F PCB.** The Rev F projects and the previous enclosure
remain preserved in `../enclosure/` and `../../hardware/`. No circuits or firmware
were removed or claimed implemented by this mechanical redesign.

## Size and architecture

- Handset: **74 × 154 × 26 mm**, versus the prior 93 × 160 × 38.8 mm body.
  About 49% less body bounding-box volume. No external screw ears. The
  illustrative trackball rises 2.3 mm above the face; quoted body sizes exclude it.
- Proposed new main board: **66 × 142 × 1.6 mm**, underside Z=17.2 mm.
  Extended 4 mm during PCB design to keep mounting drills inside the board.
  Mounting holes are [±30.5, ±68]; board corners use a 1.5 mm clip.
- Battery: MakerFocus **3000 mAh**, nominal 65 × 36 × 10 mm, supplier tolerance
  ±2 mm. Cradle reserves **38 × 67 × 12 mm**, at [0, -39], with lead exit,
  rounded guides and soft-strap anchors. No forced compression of the pouch.
- Smaller touchscreen candidate: EastRising **ER-TFT024IPS-3** rotated to
  landscape. The LCD is 59.26 × 42.72 × 2.3 mm; the CAD reserves
  **60.5 × 43.5 × 3.5 mm** pending the exact capacitive-touch stack drawing,
  with a **48.5 × 36.3 mm** window at [0,42.5]. Freeze its full ordering code and
  FPC before treating it as selected.
- Trackball: retain PIM447's documented **25 × 22 × 11 mm** envelope. Proposed
  center [0,8]. A **27 × 24 mm board aperture** lets its carrier sit partly below
  the new board instead of adding thickness above it. Retention is not finalized.
- Keypad: 16 keys at X=-22.5,-7.5,7.5,22.5 and Y=-11,-26,-41,-56. Requires
  relocated switches. Print `keycap.stl` 16 times; stem height and switch travel
  are provisional. The flange sits below the face and retains each cap.
- LTE carrier: moves into a detachable **66 × 48 × 18 mm** rear pod. It adds
  **16.8 mm** locally when attached, making maximum thickness **42.8 mm**.
  The slim 26 mm body dimension is **without the LTE pod**, not the all-up phone.
  LTE calling/data require that pod until a compact integrated modem redesign.

The design reduces size by changing the packaging, not scaling down components.
The smaller screen and new switch coordinates are explicit changes to the
hardware plan; old display/PCB parts are not drop-in compatible.

## Keep every feature

See [FEATURES.md](FEATURES.md) for the complete feature-to-space/port mapping,
including power, RF, audio, storage and independent expansion requirements.
No camera is added: the user removed it in the prior design history.

The LTE pod uses its own power/UART/control/audio harness through the upper
rear opening. **Do not power LTE from J16.** A separate lower opening reserves
J16 access; the pod's side cable exit keeps that connection accessible while
LTE is attached. A future powered accessory interface is required where a
module exceeds J16's existing 3.3 V/50 mA budget or needs 5 V.

The pod has approximately 61.2 × 43.2 × 15.8 mm internal space before pillars.
A 44.45 × 31.75 × 12.44 mm modem carrier fits the central nominal envelope with
thin foam and no stacked connectors. Its real harness bends, SIM orientation,
antenna and US-compatible replacement still need selection. Optional NFC/RFID
accessories require their own pod/coil arrangement; the LTE pod is not claimed
to hold LTE, NFC and RFID together. They can use the independent accessory
connection after its electrical/power contract is redesigned.

## Files

| File | Purpose |
|---|---|
| `handset.scad` | Editable mechanical concept and transparent `fit` envelopes |
| `exports/rear.stl` | Main body, battery cradle, revised ports and mounts |
| `exports/front.stl` | Frame, recessed face, screen opening and rectangular keys |
| `exports/keycap.stl` | One provisional retained keycap; print 16 |
| `exports/port_cover.stl` | Flush rear cover for both harness openings |
| `exports/module_pod.stl` | Removable LTE/accessory housing |
| `exports/design-preview.png` | Actual CAD geometry with illustrative display/ball/labels |
| `appearance.scad`, `exports/visual_*.stl` | Render-only props; **not printable functional components** |

Rebuild with `scripts/export_handset.sh` from repository root. Requires
OpenSCAD, Python, NumPy and Matplotlib. Preview uses a software depth buffer,
so no display server is required. Mesh checks test closed edges and connected
solids; they do not establish populated-board fit or electrical functionality.

## Assembly and remaining engineering

Main walls/face are 2.4 mm, rear floor 2.2 mm; clipped corners and a broad
1.5 mm bevel soften the edges. Internal tongue aligns the halves. Four M2
screws pass through the front columns and new board mounting holes into rear
1.7 mm pilots; start with 14 mm under-head screws, then check 5–7 mm engagement
and actual head dimensions. Dock screws engage M2 nuts inserted from inside:
approximately 6 mm for the cover, 22 mm for the pod, subject to a fit print.

Print the five parts exterior-side down as exported. Verify 0.3 mm lip/cover
clearance and 0.3 mm per-side key clearance on a small fit print first. Keycap
flanges and strap bridges may require local bridging/support. A 7 mm soft strap
holds the battery without squeezing it. The pod currently requires thin foam
or a removable adapter to retain its chosen carrier.

Speaker vents are on the upper left; a front microphone opening is at the
bottom. Top-facing IR apertures preserve transmit/receive access. Power is
left-side, USB and microSD right-side; SIM access is in the modem pod.
Port sizes and centers are targets for the new PCB, not measured positions
from Rev F. The screen, trackball carrier, speaker and RF antennas still need
measured mounting parts and exclusion zones. No drop/waterproof rating is
claimed; this remains a mechanical concept, not a manufacturing release.

Reference: the [user-supplied MAKERphone image](https://i.kickstarter.com/assets/055/040/516/5a5b513d7df97f58d78bb12ea723ae6a_original.png).
Battery dimensions: [MakerFocus 3000 mAh specification](https://www.makerfocus.com/products/makerfocus-3-7v-3000mah-lithium-rechargeable-battery-1s-3c-lipo-battery-pack-of-4).
Other existing module envelopes come from `../../docs/design/module_selection_revE.md`
and `module_inventory_revC.md`; those historical documents are not electrical
release approvals. The previous US modem/power-path blockers still apply.

## Fit checks

Run `python scripts/check_handset_fit.py` to evaluate shell-to-shell, battery,
display, proposed board, keycap, rear cover, rear pod and modem-envelope
intersections. Results are saved in `exports/fit-checks.json`. The board envelope
includes new mounting holes and the trackball aperture. A 0.001 mm offset at
seating planes excludes coincident-surface artifacts. No full populated-board,
antenna or cable-bend model is available yet.
