# MESH-PHONE

> DIY ESP32-S3 multitool / Flipper-class RF device  |  revF KiCad PCB  |  public repo

```
╔══════════════════════════════════════════════════════════════╗
║  MESH-PHONE  ::  ESP32-S3  |  CC1101 + SX1262  |  A7670SA LTE  ║
║  PN532 NFC  |  RDM6300 LF RFID  |  BB trackball + keypad    ║
╚══════════════════════════════════════════════════════════════╝
```

## Design

- 4-layer PCB, routed: power → ground → peripheral → RF/antennas
- Dual sub-GHz: CC1101 (sniff/replay) + SX1262 (Meshtastic/Reticulum)
- LTE: A7670SA  |  NFC: PN532  |  LF RFID: RDM6300
- BlackBerry trackball + 3×3 keypad on PCF8574

## Key files

| File | Purpose |
|---|---|
| `owasso1.kicad_sch` / `.kicad_pcb` | Main schematic + layout (revF) |
| `bom.csv` / `bom_priced.csv` | BOM + priced |
| `fab-output/` | Fabrication-ready Gerbers |
| `enclosure.stl` / `.scad` | 3D enclosure |

## Build notes

- KiCad 10.0.5 required (CachyOS: `LD_LIBRARY_PATH=$HOME/.local/kicad-compat` for abseil/protobuf link gap)
- Native schematic valid; DRC=0 before fab claim (see `drc.rpt` / `erc.rpt`)
- Review docs: `review-2026-09-20/`  |  GPS expansion: `revF-gps-expansion/`

## Status

RevF routed, ground islands stitched, display ground finished. Not yet verified for manufacturing.

---
Built by Jeremy Lakey (Owasso HS '27)  |  github.com/JeremyLakeyJr/mesh-phone
