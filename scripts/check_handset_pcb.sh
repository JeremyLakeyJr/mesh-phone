#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
project=hardware/handset-rev-a/generated
kicad-cli sch export netlist "$project/handset.kicad_sch" --format kicadxml -o "$project/netlist.xml"
kicad-cli sch erc "$project/handset.kicad_sch" --format json -o "$project/erc.json"
kicad-cli pcb drc "$project/handset.kicad_pcb" --schematic-parity --format json -o "$project/drc.json"
python3 scripts/verify_handset_pcb.py
if [[ -f "$project/sx1262-rf-ground-routing.json" ]]; then
  python3 scripts/check_handset_sx1262_rf_ground.py "$project"
  python3 scripts/test_handset_sx1262_rf_ground.py "$project"
fi
if [[ -f "$project/sx1262-local-rf-routing.json" ]]; then
  python3 scripts/check_handset_sx1262_local_rf.py "$project"
  python3 scripts/test_handset_sx1262_local_rf.py "$project"
fi
if [[ -f "$project/sx1262-pa-update.json" ]]; then
  python3 scripts/check_handset_sx1262_pa.py "$project"
fi
if [[ -f "$project/sx1262-rf-update.json" ]]; then
  python3 scripts/check_handset_sx1262_rf.py "$project"
fi
if [[ -f "$project/sx1262-supply-routing.json" ]]; then
  python3 scripts/check_handset_sx1262_supply.py "$project"
  python3 scripts/test_handset_sx1262_supply.py "$project"
fi
if [[ -f "$project/sx1262-regulator-routing.json" ]]; then
  python3 scripts/check_handset_sx1262_regulator.py "$project"
fi
if [[ -f "$project/audio-routing.json" ]]; then
  python3 scripts/check_handset_audio.py "$project"
  python3 scripts/test_handset_audio.py "$project"
fi
if [[ -f "$project/usb-connector-update.json" ]]; then
  python3 scripts/check_handset_usb_connector.py "$project"
fi
if [[ -f "$project/usb-data-update.json" ]]; then
  python3 scripts/check_handset_usb_data.py "$project"
  python3 scripts/test_handset_usb_data.py "$project"
fi
if [[ -f "$project/core-routing.json" ]]; then
  python3 scripts/check_handset_core.py "$project"
  python3 scripts/test_handset_core.py "$project"
fi
if [[ -f "$project/keypad-routing.json" ]]; then
  python3 scripts/check_handset_keypad.py "$project"
  python3 scripts/test_handset_keypad.py "$project"
  python3 scripts/check_handset_keypad_firmware.py
  python3 scripts/check_handset_bringup.py
fi
python3 scripts/check_handset_modem_power.py
python3 scripts/check_handset_system_power.py
python3 scripts/check_handset_display_expansion.py
if [[ -f "$project/expansion-update.json" ]]; then
  python3 scripts/check_handset_expansion.py "$project"
fi
if [[ -f "$project/expansion-ground-update.json" ]]; then
  python3 scripts/test_handset_expansion_ground.py "$project"
fi
if [[ -f "$project/backlight-update.json" ]]; then
  python3 scripts/check_handset_backlight_routing.py "$project"
fi
if [[ -f "$project/display-routing.json" ]]; then
  python3 scripts/check_handset_display_routing.py "$project"
fi
if [[ -f "$project/battery-copper-update.json" ]]; then
  python3 scripts/check_handset_battery_copper.py "$project/handset.kicad_pcb"
fi
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
if [[ -f "$project/sx1262-clock-update.json" ]]; then
  python3 scripts/check_handset_sx1262_clock.py "$project"
  python3 scripts/test_handset_sx1262_clock.py "$project"
fi
if [[ -f "$project/power-supervisor-update.json" ]]; then
  python3 scripts/check_handset_power_supervisor.py "$project"
fi
if [[ -f "$project/charge-inhibit-update.json" ]]; then
  python3 scripts/check_handset_charge_inhibit.py "$project"
fi
if [[ -f "$project/supervisor-routing.json" ]]; then
  python3 scripts/check_handset_supervisor_routing.py "$project"
fi
if [[ -f "$project/main-distribution.json" ]]; then
  python3 scripts/check_handset_main_distribution.py "$project"
fi
if [[ -f "$project/reg18-routing.json" ]]; then
  python3 scripts/check_handset_reg18.py "$project"
fi
if [[ -f "$project/reg18-distribution.json" ]]; then
  python3 scripts/check_handset_reg18_distribution.py "$project"
fi
if [[ -f "$project/reg5-routing.json" ]]; then
  python3 scripts/check_handset_reg5.py "$project"
fi
if [[ -f "$project/reg5-distribution.json" ]]; then
  python3 scripts/check_handset_reg5_distribution.py "$project"
fi
if [[ -f "$project/modem-routing.json" ]]; then
  python3 scripts/check_handset_modem.py "$project"
fi
kicad-cli sch export pdf "$project/handset.kicad_sch" -o "$project/handset-schematic.pdf"
kicad-cli sch export svg "$project/handset.kicad_sch" -o "$project/previews/"
kicad-cli pcb export svg "$project/handset.kicad_pcb" --mode-single --layers F.Cu,F.SilkS,Edge.Cuts,User.2 --page-size-mode 2 -o "$project/previews/board-front.svg"
kicad-cli pcb export svg "$project/handset.kicad_pcb" --mode-single --layers B.Cu,B.SilkS,Edge.Cuts,User.1 --page-size-mode 2 -o "$project/previews/board-back.svg"
kicad-cli pcb export svg "$project/handset.kicad_pcb" --mode-single --layers F.Fab,Edge.Cuts --page-size-mode 2 -o "$project/previews/assembly-front.svg"
kicad-cli pcb export svg "$project/handset.kicad_pcb" --mode-single --layers B.Fab,Edge.Cuts --page-size-mode 2 -o "$project/previews/assembly-back.svg"
if [[ -f "$project/expansion-ground-update.json" ]]; then
  for layer in In1 In2; do
    kicad-cli pcb export svg "$project/handset.kicad_pcb" --mode-single --layers "$layer.Cu,Edge.Cuts" --page-size-mode 2 -o "$project/previews/expansion-ground-$layer.svg"
  done
fi
# Native ERC/DRC findings are retained in JSON; this script tests artifact integrity.
# It does not suppress errors or declare the design electrically released.
