# MESH-PHONE

ESP32-S3 handheld hardware with sub-GHz radios, LTE, NFC/RFID, a 4×4 keypad,
trackball, GPS and a rear expansion connector. Engineering prototype; electrical
release blockers remain documented in the revision notes.

## Project layout

| Directory | Contents |
|---|---|
| [hardware/rev-f](hardware/rev-f/README.md) | Active GPS/expansion revision; open `mesh-phone.kicad_pro` |
| `hardware/main/` | Preserved original KiCad project and its local footprints |
| [mechanical/handset](mechanical/handset/README.md) | Latest reference-inspired handset concept; requires new PCB |
| [mechanical/enclosure](mechanical/enclosure/README.md) | Preserved enclosure for the existing Rev F board |
| `scripts/` | Maintained geometry extraction and revision verification |
| `docs/design/` | Historical design notes, pin budgets and routing notes |
| `docs/reviews/` | Electrical review evidence |
| `manufacturing/` | BOMs and explicitly unreleased legacy fabrication exports |
| `archive/` | Prior PCB candidates, enclosure and one-off development scripts |

## Working with the project

Open `hardware/rev-f/mesh-phone.kicad_pro` in KiCad. Keep each project's symbol
and footprint libraries beside it. Existing legacy library names are preserved;
the library tables point to the actual `mesh-phone.pretty` directories.

Run `python scripts/verify_revF.py` from the repository root to check the saved
netlist and placement contracts. This uses the saved DRC/ERC reports, not a new
native electrical analysis. Export a fresh netlist and native reports after
circuit changes. KiCad 10.0.5 was used for the existing checkpoint.

Run `python scripts/enclosure_geometry.py` after PCB mechanical changes, then
`scripts/export_enclosure.sh` to rebuild the enclosure STLs and preview.
See the mechanical README for panel-placement assumptions and fit checks.

Archived scripts preserve historical experiments, including obsolete absolute
paths and old project names. They are not a supported build pipeline and should
not be replayed on the active board. `.history/` is the existing KiCad history
repository and remains in place.

Latest appearance: [handset preview](mechanical/handset/exports/design-preview.png).
See [feature preservation](mechanical/handset/FEATURES.md) for the retained hardware
requirements and explicit packaging changes. Build with `scripts/export_handset.sh`.
The selected new-board materials list is in
[`hardware/handset-rev-a/materials-to-use.csv`](hardware/handset-rev-a/materials-to-use.csv).
The supporting component research and comparison table are in
[`docs/research/new-pcb-component-study.md`](docs/research/new-pcb-component-study.md)
and [`hardware/handset-rev-a/candidate-components.csv`](hardware/handset-rev-a/candidate-components.csv).
