#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
project=hardware/handset-rev-a/generated
kicad-cli sch export netlist "$project/handset.kicad_sch" --format kicadxml -o "$project/netlist.xml"
kicad-cli sch erc "$project/handset.kicad_sch" --format json -o "$project/erc.json"
kicad-cli pcb drc "$project/handset.kicad_pcb" --schematic-parity --format json -o "$project/drc.json"
python3 scripts/verify_handset_pcb.py
if [[ -f "$project/reg3-routing.json" ]]; then
  python3 scripts/check_handset_3v3.py "$project/handset.kicad_pcb"
fi
if [[ -f "$project/power-entry-update.json" ]]; then
  python3 scripts/check_handset_power_entry.py "$project/handset.kicad_pcb"
  python3 scripts/check_handset_charger_policy.py
fi
if [[ -f "$project/cc1101-update.json" ]]; then
  python3 scripts/check_handset_cc1101.py "$project"
fi
if [[ -f "$project/sx1262-power-update.json" ]]; then
  python3 scripts/check_handset_sx1262_power.py "$project"
fi
kicad-cli sch export pdf "$project/handset.kicad_sch" -o "$project/handset-schematic.pdf"
kicad-cli sch export svg "$project/handset.kicad_sch" -o "$project/previews/"
kicad-cli pcb export svg "$project/handset.kicad_pcb" --mode-single --layers F.Cu,F.SilkS,Edge.Cuts,User.2 --page-size-mode 2 -o "$project/previews/board-front.svg"
kicad-cli pcb export svg "$project/handset.kicad_pcb" --mode-single --layers B.Cu,B.SilkS,Edge.Cuts,User.1 --page-size-mode 2 -o "$project/previews/board-back.svg"
kicad-cli pcb export svg "$project/handset.kicad_pcb" --mode-single --layers F.Fab,Edge.Cuts --page-size-mode 2 -o "$project/previews/assembly-front.svg"
kicad-cli pcb export svg "$project/handset.kicad_pcb" --mode-single --layers B.Fab,Edge.Cuts --page-size-mode 2 -o "$project/previews/assembly-back.svg"
# Native ERC/DRC findings are retained in JSON; this script tests artifact integrity.
# It does not suppress errors or declare the design electrically released.
