# USB4105 ground-land clearance correction — 2026-10-06

The four native USB1 hole-clearance findings are eliminated. Native DRC now
reports zero findings, with zero schematic parity findings and 285 unconnected
items. This completes the nominal CAD clearance correction, not board release.

## Geometry and evidence

The installed footprint is `Handset:USB4105_GroundCornerRelief`. USB4105,
its location/orientation, all locating and shell holes, pad centers, pad
bounding dimensions, nets and all 7,860 track/via items are retained. The
0.25 mm hole-clearance rule and all other board rules are unchanged.

The old round-rectangle ground lands were only 0.1944 mm from the locating
holes. A 0.30 mm chamfer on each hole-facing heel corner gives 0.263302 mm
nominal clearance. A1/B12 and A12/B1 are duplicate electrical pad numbers
on two physical lands; their overlapping shapes are changed together.

The [GCT USB4105 B4 drawing](https://gct.co/files/drawings/usb4105.pdf)
(18 December 2023, sheet 1) supplies the nominal hole and land dimensions.
The contour here is an **engineered modification of the recommended land
pattern**, not an unmodified or manufacturer-approved footprint. The 0.60 ×
1.15 mm land envelope and 0.65 mm locating holes remain intact. Only the
hole-facing corner beneath the connector is relieved; the terminal-facing
part of the land remains. An independent geometry check verifies a continuous
0.45 × 0.75 mm central solder rectangle in each ground land. That rectangle
is a design retention criterion, not a substitute for assembler approval or
a measured solder joint. Nominal CAD clearance does not include a fabricated
hole-registration tolerance analysis.

No connector substitution, drill shrinkage, moved holes, clearance exception
or DRC exclusion is used. The custom library footprint and schematic
assignment agree with the PCB. `prepare_handset_usb_connector.py` stages the
change and refuses to overwrite an installed revision.

## Verification and preservation

- Four regression tests pass: actual geometry, rejection of the original
  corner clearance, rejection of smaller locating holes, and rejection of a
  smaller ground land.
- All 118 local power-entry pad connections pass, including connector power,
  CC and ground. USB D+/D− routing is outside that continuity check.
- The full board check verifies all prior circuits and refreshes native reports
  and previews. The manufacturing release gate independently checks the USB
  land geometry and continues to block release for unfinished work.
- The previous board, rules, schematic sheet and verification reports are in
  [`archive/handset-before-usb-relief/ef24884f9bbb`](../../archive/handset-before-usb-relief/ef24884f9bbb).
- Exact source/final hashes and scope are in
  [generated/usb-connector-update.json](generated/usb-connector-update.json);
  measured clearances are in
  [generated/usb-connector-check.json](generated/usb-connector-check.json).

## Remaining work

Finish USB data routing against the selected stackup and qualify ESD, signal
integrity, source-current behavior and connector fit. Freeze the actual
USB4105 ordering suffix and obtain assembler DFM approval of the modified
land contour and solder process. The rest of the board still has 30 ERC
findings, 285 unconnected items and eleven open engineering blocker groups.
It is not released for fabrication or power-up.
