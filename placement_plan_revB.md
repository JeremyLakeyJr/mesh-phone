# OWASSO-1 Rev B placement baseline

Board outline: 56 mm x 122 mm, four copper layers.

## Mechanical stack

- Flat LiPo pocket: 54 x 38 x 12 mm nominal clearance, under the lower half of the PCB.
- Display: front/top, connected through an FPC connector so display adapter boards can be changed.
- Camera: top edge, aligned with the case lens opening.
- Trackball: lower/front user-input area.
- Keypad: lower/front 3x3 matrix, aligned to the case grid.
- USB-C: bottom edge.
- SIM and microSD: opposite side edges for access without opening the case.

## RF placement

- LTE module: central/lower region, antenna routed to a dedicated side/top keepout.
- CC1101: left edge with its own sub-GHz antenna exit.
- SX1262: right edge with its own antenna exit.
- NFC antenna: top/front region, outside the ESP32 and LTE antenna keepouts.
- LF RFID coil: perimeter/inner-layer spiral; no copper or battery directly underneath the active coil area.
- ESP32 antenna: keep clear of LTE, CC1101, SX1262, battery, and copper pours.

## Power placement

- Charger, protection, fuel gauge, and USB input stay grouped at the lower edge.
- LTE power converter and bulk capacitors stay immediately beside the LTE module.
- 3.3 V regulator stays beside the ESP32/peripheral power entry.
- Battery connector is on the lower board edge with polarity and test points clearly marked.

## Layout lock conditions

- Do not lock the display FPC footprint until the exact panel/adapter pin order is chosen.
- Do not lock the camera FPC footprint until the exact OV2640 module pin order is chosen.
- Do not route LTE RF until the exact A7670SA carrier board and antenna connector are chosen.
- Keep the battery connector mechanically accessible and strain-relieved in the printed case.
