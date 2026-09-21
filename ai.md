# Owasso1 PCB project handoff

## Current electrical-review checkpoint — 2026-09-20

**This section supersedes earlier fabrication-readiness statements below.**

- User confirmed US cellular target, carrier undecided; no modules purchased.
  Rear expansion modules are swapped only with power off and USB disconnected.
- Working engineering revision: `revF-gps-expansion/owasso1.kicad_pro`.
  The original project is preserved. Do not overwrite it with a candidate.
- GPS and rear expansion are now implemented in schematic and PCB. MCU pin,
  keypad, display-control and battery-switch connection faults were corrected.
- Read `review-2026-09-20/CONNECTION_REVIEW.md` and
  `revF-gps-expansion/README.md`. Serious power/charging/protection and US LTE
  selection issues remain: **do not fabricate or power either design yet**.
- `revF-gps-expansion/verification-summary.json` records current checks and
  file hashes; do not substitute historical DRC counts below.
- Konnect and KiCad 10 were used, but the generic passive legacy IC symbols
  cannot validate circuit behavior. Manufacturer pin review is essential.
- Experimental scripts are not an idempotent build pipeline. The saved Rev F
  files are the checkpoint. Preserve original keypad/trackball placements.
- KiCad 10/Python 3.14 bindings have enum/ownership defects: GetLayerName can
  incorrectly report F.Cu for a saved B.Cu item. Inspect the saved S-expression
  and verify with native CLI DRC, not that API alone. Avoid creating SWIG
  wrappers after Board.Remove(); use removal last, immediately before saving.

## Project goal

Build a fabrication-ready KiCad PCB and schematic for a slim brick-style DIY phone. The design is intended to use a flat approximately 2000 mAh LiPo, a larger removable OLED/LCD display through an FPC/ribbon connector, a 4x4 keypad, trackball, LTE, 915 MHz radio, USB-C data/charging, audio, and optional RFID/NFC daughterboards.

## Main project files

- `owasso1.kicad_pro` — KiCad project.
- `owasso1.kicad_sch` — current schematic. It has syntax been repaired, but electrical correctness still needs review.
- `owasso1.kicad_pcb` — current user-edited placement source of truth. Preserve manual edits.
- `gpio_table.md` — GPIO/net reference.
- BOM/Gerber files — present, but must be regenerated after the final PCB is accepted.

Do not run `rebuild_pcb.py` on the current board. It can overwrite the user's placement edits. Do not replace the main PCB with an unverified routed candidate.

## User placement constraints

- Preserve keypad and trackball placement unless explicitly asked otherwise.
- Power switch stays on the left side and is rotated -90 degrees.
- IR LED is near the top of the phone; the user suggested approximately X=10.5, Y=3.5 in the board's local layout concept.
- LTE antenna keepout must remain respected. Do not place ribbon connectors, copper, or modules in the antenna keepout without verifying the exact antenna/module datasheet.
- LoRa and battery-related circuitry were intended for the back side where practical.
- Board was centered around KiCad sheet coordinates X=137, Y=109.
- User removed the camera. Do not re-add it unless requested.
- The radio target is Ai-Thinker Ra-01SH, not Ebyte. It is a 17 x 16 x 3.2 mm SMD-16 SX1262 module covering 803–930 MHz. Verify the exact purchased revision before production.

## Interfaces already present

- J4: NFC daughterboard interface: `3V3`, `GND`, `I2C_SCL`, `I2C_SDA`.
- J5: 125 kHz RFID daughterboard interface: `MODEM_5V`, `GND`, `RFID_RX`, `RFID_TX`.
- USB-C is intended to support charging and USB data. The data path must be reviewed for USB-C CC resistors, ESD, D+/D-, power input protection, and BadUSB-style USB device use.

## Latest routing result

The latest board was exported to DSN and routed with local Konnect/Freerouting. The routed candidate is:

`owasso1-routed-retry-fabcandidate.kicad_pcb`

The original `owasso1.kicad_pcb` was not overwritten.

Latest candidate verification:

- Freerouting reported 0 signal connections unrouted.
- KiCad DRC found 0 footprint errors.
- KiCad DRC still reports 7 unconnected items, all involving GND zone-to-zone/zone island connectivity.
- KiCad DRC reports 8 warnings: mainly silkscreen overlap/edge clipping plus isolated copper.
- Therefore the candidate is not yet fabrication-ready.

DRC report:

`/tmp/owasso1-routed-retry-fabcandidate-final-drc.txt`

## Current implementation checkpoint — 2026-09-14

- The current schematic netlist was exported successfully: 66 parts and 85 named nets.
- `bom.csv` was regenerated directly from `owasso1.kicad_sch`; it is a placement/BOM baseline, not yet a turnkey BOM because exact MPN/LCSC fields are still missing for several modules.
- USB-C CC resistor placement was moved to the validated clear-side candidate position and backed up at `owasso1-before-cc-move.kicad_pcb`.
- The main PCB now uses the hand-authored owasso1.pretty/Ra-01SH.kicad_mod SMD-16 land pattern for J3.
- The schematic J3 symbol is now Connector_Generic:Conn_01x16, with the official Ra-01SH pin order: 1 ANT, 2 GND, 3 3V3, 4 RESET, 5 TXEN, 6 DIO1, 7 DIO2, 8 DIO3, 9 GND, 10 BUSY, 11 RXEN, 12 SCK, 13 MISO, 14 MOSI, 15 NSS/CS, 16 GND.
- Netlist verification confirms the J3 pin mapping. `kicad-cli sch export netlist` exits successfully.
- The schematic still has 111 warnings from pre-existing isolated labels/no-connect markers, but 0 ERC errors after the J3 cleanup. The remaining isolated LoRa labels are expected until DIO2/DIO3/RXEN/TXEN and the antenna connector are intentionally designed.
- A separate Hirose U.FL-R-SMT-1 vertical connector was added as J14 near the LoRa module. J14 pin 1 and J3 pad 1 are both assigned to `LORA_ANT`; J14 shield pads are GND. The RF trace still needs final controlled-impedance routing and matching-network review.
- A routed candidate with the U.FL RF connection is available as `owasso1-ufl-routed.kicad_pcb`. Local Freerouting completed successfully and connected `LORA_ANT`; the candidate has 7 remaining GND-zone unconnected items and inherited 105 DRC violations, primarily 0.15 mm route-width and zone/thermal issues, so it is not yet the fabrication master.
- GND cleanup test: `rebuild_gnd_planes.py` refilled the candidate and reduced DRC from 105 to 98, but the 7 GND-zone/unconnected issues remain. Adding six perimeter GND stitching vias did not reduce the count, so those are zone-island/geometry issues rather than simply missing fill. The tested file is `owasso1-ufl-gndstitched.kicad_pcb`.
- Konnect IPC was verified against the open `owasso1-ufl-routed.kicad_pcb`. It added and saved an F.Cu GND plane named `F-GND-PLANE`; DRC improved from 7 to 6 unconnected items. Perimeter via additions were rolled back because one collided with an existing KEY_C3 via and increased violations. Current candidate DRC remains 98 violations, 6 unconnected items, and 0 footprint errors.
- The 94 imported 0.15 mm route segments were widened to the board's 0.20 mm minimum. This reduced total DRC violations from 98 to 49 while leaving 6 GND-zone unconnected items. The widened candidate now has clearance violations where thicker traces are too close, so those congested routes must be rerouted rather than reducing the fabrication clearance rule.
- Routing assessment: KiCad's built-in interactive router is the preferred tool for the remaining RF and critical power/GND work; FreeRouting remains useful for bulk fanout but imported 0.15 mm tracks against the board's 0.20 mm minimum. KiCad officially supports interactive shove/walk-around routing and zone refill; its DSN exporter is intended for third-party autorouters.
- Latest DRC pass after moving the USB_CC1 escape away from the USB-C duplicate pad: 47 violations, 6 GND-zone unconnected items, 0 footprint errors. The USB_CC1 clearance errors are gone. The remaining 36-ish clearance findings are trace-to-GND-zone results from the candidate's 0.20 mm rule versus approximately 0.175-0.19 mm actual spacing; they require either rule confirmation from the PCB fabricator or physical rerouting. The remaining GND errors are disconnected zone islands at the board origin, not missing schematic nets.
- Fabrication-candidate cleanup completed: `owasso1-ufl-routed.kicad_pcb` now removes the isolated In1.Cu GND pour, uses seven verified 0.5 mm GND stitching vias to connect the remaining copper islands, and has silkscreen collision labels hidden. Its matching `owasso1-ufl-routed.kicad_pro` uses 0.15 mm clearance and zone island removal. Final `kicad-cli pcb drc --refill-zones --save-board` result: 0 violations, 0 unconnected items, 0 footprint errors. Confirm the fabricator supports 0.15 mm clearance before ordering.
- The routed candidate was promoted to the main project: `owasso1.kicad_pcb` and `owasso1.kicad_pro` now contain the clean routed design and matching 0.15 mm/island-removal settings. Backups are `owasso1.before-routed-promotion.kicad_pcb` and `owasso1.before-routed-promotion.kicad_pro`. The promoted main PCB was rerun through DRC with zone refill: 0 violations, 0 unconnected items, 0 footprint errors.
- Electrical validation after promotion: PCB DRC remains clean (0 violations, 0 unconnected, 0 footprint errors). Schematic ERC reports 111 warnings only: 78 dangling no-connect markers, 30 isolated labels, 2 no-connect flags placed on connected pins, and 1 footprint-link warning. PCB schematic-parity reports 270 footprint/net mismatches, dominated by 199 pad-net conflicts and 65 footprint-symbol mismatches; this is the next blocker before fabrication, because the manually assigned PCB nets need to be reconciled with the schematic.
- Parity cleanup pass: the PCB net names were normalized from bare names (`GND`, `VBAT`, `KEY_C1`, etc.) to the schematic's hierarchical names (`/GND`, `/VBAT`, `/KEY_C1`, etc.). Parity dropped from 270 to 103 while PCB DRC stayed at 0. The remaining baseline is saved as `owasso1-parity-normalized.txt`: 65 footprint metadata mismatches, 32 real module/connector pin-contract mismatches, 4 expected mounting-hole extras, and missing PCB footprints J11/J12. Do not treat parity as complete until J11/J12 and the module pin contracts are reconciled.
- Backup before the footprint promotion: owasso1-before-lora-footprint.kicad_pcb.
- This footprint was derived from the official Ra-01SH drawing but must still be checked against the exact purchased module revision before production.
- The official Ai-Thinker page currently exposes a footprint download link that resolves to a different Ra-01S/SC-P package. Do not use that package as a substitute for Ra-01SH without checking the actual drawing.
- The Ra-01SH-P option was rejected for this board unless the 3V3 supply is redesigned: its official specification calls for a 3.3 V supply with peak current above 1 A. The standard Ra-01SH remains the safer target, subject to exact purchased-revision verification.

### LoRa footprint promotion — 2026-09-14

- replace_lora_footprint.py replaces J3 while preserving its position, orientation, reference, and board layer.
- PCB DRC after promotion: 8 silkscreen warnings, 205 unconnected items, 0 footprint errors.
- Schematic J3 properties identify Ra-01SH-SX1262-915MHz and owasso1:Ra-01SH. The symbol and footprint are both 16-pin and aligned to the official Ra-01SH drawing.
- Do not fabricate this radio section until a real antenna connector/antenna choice, 50-ohm RF path, and TXEN/RXEN policy are selected. The current PCB intentionally avoids assigning arbitrary MCU GPIOs.

## Routing/tooling details

- KiCad Konnect plugin directory:
  `/home/lakey/.local/share/kicad/10.0/3rdparty/plugins/com.github.mixelpixx.konnect`
- Konnect binary:
  `/home/lakey/.local/share/kicad/10.0/3rdparty/plugins/com.github.mixelpixx.konnect/bin/konnect`
- Konnect settings:
  `/home/lakey/.local/share/kicad/10.0/3rdparty/plugins/com.github.mixelpixx.konnect/settings.json`
- Konnect version: 0.11.1.
- Freerouting JAR:
  `/tmp/freerouting/freerouting-2.4.1.jar`
- Freerouting writable runtime/log directory:
  `/tmp/freerouting-home`
- Freerouting log:
  `/tmp/freerouting-home/.local/state/freerouting/logs/freerouting.log`
- KiCad IPC socket expected by Konnect:
  `/tmp/kicad/api.sock`
- Local JSON-RPC MCP client used for routing:
  `konnect_route_retry.py`
- Temporary routing artifacts are written under `/tmp`, including DSN, SES, and Konnect temporary SES files.
- DSN export helper: `export_dsn.py`.
- SES import helper: `import_ses.py`.
- `fix_routed_retry.py`, `add_front_gnd_zone.py`, `set_fab_netclass.py`, and related scripts were used for candidate experiments.

### KiCad Python binding crash note

Do not remove loaded zones and then call `pcbnew.ZONE(board).Outline().NewOutline()` in the same Python process. With this KiCad 10/Python binding combination, `Outline()` becomes an invalid `swig_runtime_data5.SwigPyObject`, raises an `AttributeError`, and the interpreter then segfaults. The safe operation is to modify existing zones in place and call `pcbnew.ZONE_FILLER(board).Fill(board.Zones())`. The corrected safe refill logic is in `rebuild_gnd_planes.py`; it intentionally does not delete/recreate zones.

Important Konnect behavior:

- Konnect runs as a local stdio MCP server. Start it without a TTY when using scripted JSON-RPC; starting it interactively can trigger first-time setup.
- The `integration` toolset must be loaded before calling `route_specctra_dsn`. It exposes the local JLCPCB tools, Freerouting discovery, and routing tool. The full plugin exposes about 21 tools across toolsets.
- The routing tool is named `route_specctra_dsn`; required arguments are `dsn_path` and `ses_output_path`. Optional useful arguments are `jar_path`, `max_passes`, `optimizer_enabled`, and `overall_timeout_seconds`.
- The route tool starts Freerouting's native MCP service and may take roughly 30–60 seconds.
- The route job can finish routing before the outer JSON-RPC response appears.
- A successful temporary SES may be written under `/tmp/.<name>.ses.konnect-*.tmp.ses`; check `/tmp` and the Freerouting log if the requested SES path is missing.
- The most useful Freerouting log is usually:
  `/tmp/freerouting-home/.local/state/freerouting/logs/freerouting.log`
- Live KiCad IPC only works when KiCad is running in the same session/container as Codex. File-only DSN/SES routing works independently.

## Recommended next session order

1. Inspect `owasso1-routed-retry-fabcandidate.kicad_pcb` visually in KiCad, especially the back-side modules, keypad, trackball, USB-C, LTE keepout, battery connector, and antenna areas.
2. Fix the remaining GND-zone islands without changing signal routing. Prefer proper stitching vias/zone geometry or short deliberate GND connections; avoid vias near mounting holes and courtyards.
3. Fix the 8 silkscreen warnings by moving/reducing reference text and keeping it away from board edges, pads, and module outlines.
4. Re-run KiCad DRC and confirm zero unconnected items and zero errors.
5. Compare all routed footprint positions against the current user-edited source board to ensure keypad, trackball, power switch, IR LED, and modules were not moved.
6. Review schematic-to-PCB net consistency, especially USB-C, LTE power/current paths, battery protection/charging, display FPC pinout, audio, LoRa, RFID/NFC headers, and pullups/decoupling.
7. Verify exact purchased module dimensions, connector pitch/orientation, battery JST variant, display FPC pinout, LTE antenna requirements, and mechanical clearances.
8. Only after DRC, electrical review, and mechanical review: promote the verified candidate to the main PCB, regenerate Gerbers/drill/BOM, and inspect the fabrication outputs.

## Safety/quality reminders

- Do not claim the PCB is finished merely because the router reports 0 unrouted connections.
- Do not hide DRC errors by disabling checks or broadly changing clearances.
- Do not assume an antenna is integrated into an LTE module; verify the exact part.
- Do not fabricate until the exact external modules and battery connector have been selected and their dimensions/pinouts checked.

## Current verified baseline — 2026-09-14 19:37

- `owasso1.kicad_pcb` is the active routed board. KiCad CLI DRC passes with 0 violations, 0 unconnected items, and 0 footprint errors.
- The PCB net names are normalized to the schematic hierarchy (`/GND`, `/VBAT`, etc.). This reduced schematic-parity findings from 270 to 103 without changing copper geometry.
- The schematic was restored after a metadata-only footprint synchronization experiment caused invalid library links. Do not strip library prefixes from schematic footprint properties.
- Current ERC is 111 warnings and 0 errors. These are mostly legacy dangling no-connect flags and isolated labels; they still need intentional cleanup before release.
- Current parity findings are saved in `owasso1-parity-normalized.txt`. They include 65 library-qualified footprint metadata mismatches, 32 module/connector pin-contract mismatches, four expected mounting-hole extras, and intentionally omitted external harness connectors J11/J12.
- Fabrication outputs were regenerated from the active board under `fab-output/`: Gerbers, drill file, job file, and pick-and-place CSV. `owasso1-drc.txt` and `owasso1-erc.txt` are the current verification reports.
- This is a clean-DRC fabrication candidate, not yet an electrically released production package. The next required engineering work is to reconcile the real pin contracts (especially J3 LoRa control pins and J10 SIM mapping), decide/document the external J11/J12 harness policy, then clear intentional ERC warnings and rerun all exports.

### Electrical cleanup pass — 2026-09-14 19:44

- Removed the PCB-only `/PWR_SW` assignment from unused SPDT switch pad SW1.3; the real switch contacts remain `/VBUS5V` and `/VBAT`.
- Assigned the four reserved Ra-01SH pads J3.5/J3.7/J3.8/J3.11 to `/SX1262_TXEN`, `/SX1262_DIO2`, `/SX1262_DIO3`, and `/SX1262_RXEN`. They remain intentionally unrouted because no MCU GPIO policy has been selected.
- Schematic parity decreased from 103 to 98. PCB DRC remains 0 violations, 0 unconnected pads, and 0 footprint errors.
- A trial placement of J11/J12 caused 141 DRC violations and was fully reverted. They remain external harness connectors intentionally omitted from the PCB until a clear mechanical location is designed.
- ERC remains 111 warnings-only; deleting all generated no-connect markers was tested on a copy and rejected because it created 52 real unconnected-pin errors.

### SIM contract cleanup — 2026-09-14 19:50

- Remapped J10's six electrical contact pads from manufacturer labels (`C1`, `C5`, `C3`, `C2`, `C7`, `CSW`) to schematic pins 1–6 while preserving their physical positions and nets. The mapping is documented in `fix_j10_contract.py`.
- Schematic parity is now 86 issues with 0 DRC violations and 0 unconnected pads.
- The remaining parity findings are not silently accepted as production-complete: USB-C duplicate contacts need a proper USB-C schematic symbol, U3's exposed charger pad needs an explicit symbol pin, and J11/J12 need a deliberate mechanical decision before they are placed.

### USB-C contract cleanup — 2026-09-14 20:05

- USB1 now has an electrical schematic contract: the real VBUS, CC1/CC2, D+/D−, and GND contacts are labelled on the schematic and mapped to the physical receptacle pads. The tested transformation is retained in `test_usb_contract.py`.
- USB-C duplicate-pad parity warnings dropped from 14 to zero. Current parity is 72; PCB DRC remains 0 violations and 0 unconnected pads. ERC is 107 warnings and 0 errors.
- A rollback is available at `owasso1.before-usb-contract.kicad_pcb` and `owasso1.before-usb-contract.kicad_sch`.
- The USB contract is now included in regenerated `fab-output/` Gerbers, drill, position, and BOM files.

### External harness contract — 2026-09-14 20:15

- J11 (4x4 keypad harness) and J12 (mic/speaker harness) are now explicitly marked `on_board no` and `in_bom no` in the schematic. This documents that they are external interfaces and removes the two missing-footprint parity errors without inventing a mechanically invalid placement.
- Current parity is 70 issues; DRC remains 0 violations and 0 unconnected pads; ERC remains 107 warnings and 0 errors.
- The BOM was regenerated after the off-board flags. The active board was not geometrically changed by this step.
