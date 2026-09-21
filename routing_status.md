# OWASSO-1 routing status

The working board is a regenerated 87 x 154 mm placement candidate based on
the corrected controlled netlist.

- The previous routed board was preserved at
  `/tmp/owasso1-before-pinmap-correction.kicad_pcb` and was not retained as
  the working board because its ESP32 signal assignments were wrong.
- ESP32-S3-WROOM-1 module-pad-to-GPIO mapping is now explicit and has zero
  duplicate U1 pad assignments.
- PCF8574, display FPC, camera FPC ordering, Molex microSD contact mapping,
  raw-camera regulators, and TPS61023 boost pinout were corrected in
  `augment_netlist_revD.py`.
- The charger/protection, boost, USB-C, IR, battery, and small-signal support
  parts were regrouped for local routing. The four-by-four keypad field and
  external connector clearances were re-spaced around those groups.
- SW1 was moved from the center to the left board wall at `(8,55)` for
  side-accessible power control without introducing electrical or placement
  DRC errors.
- The schematic was regenerated from the corrected netlist metadata and now
  contains 66 parts and 86 nets. ERC still needs the final routed-board pass;
  isolated external-module labels and no-connect markers are expected to need
  cleanup.
- The camera subsystem was removed from the authoritative design: J8, U9/U10,
  C5-C8, R6/R7, all `CAM_*` nets, and the ESP32 camera GPIO assignments are
  absent from the regenerated netlist, schematic, and PCB. The design now has
  66 parts and 86 nets.
- J3 is now the Ebyte E22-900M22S 915 MHz SX1262 module. Its generic 1x09
  adapter was replaced by the project-local 22-pad E22 land pattern and the
  physical pad mapping was corrected. The board outline is now 87 x 154 mm so
  J3 fits at the upper-right without footprint-envelope overlap.
- The board is still unrouted: the current PCB DRC reports 212 unconnected
  items and zero track segments. Placement/copper DRC is clean; the remaining
  10 findings are silkscreen warnings only. A release Gerber set must not be generated from
  this placement-only board until routing is completed.
- The source electrical decisions are documented in `connection_audit.md`.
- No Gerber release is valid from this placement until the camera module type,
  camera regulators, boost IC, and schematic are finalized.

FreeRouting was run against the corrected placement and produced
`/tmp/owasso1-current.ses`: 1,194 track segments were generated and only four
connections remain unrouted (VBAT to SW1, CAM_D0, CAM_D1, and LTE_RI). The
candidate boards `owasso1-routed-candidate.kicad_pcb` and
`owasso1-routed-normalized.kicad_pcb` are preserved for review. They are not
promoted to the release board yet because the imported candidate still has
DRC errors, including 20 unconnected items and fabrication-rule violations.
The next valid step is to resolve those four nets and the imported-board DRC
issues, then promote the verified route to `owasso1.kicad_pcb`.
