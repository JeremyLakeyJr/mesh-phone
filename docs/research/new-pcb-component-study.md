# Compact handset PCB component study

Research checkpoint: 2026-09-21. This is a selection study for a new PCB, not
an electrical release. Dimensions and capabilities come from manufacturer
product pages and datasheets linked below. Distributor listings and generic
marketplace modules were not used as design authority.

Implementation update: [Handset Rev A](../../hardware/handset-rev-a/README.md)
uses a 66 × 142 mm outline to preserve mounting-hole edge material. The user
requires multi-carrier cellular service, so A7672G is not frozen as the modem.
The UBX-M10050-KB integration manual is listed by u-blox as NDA-required;
its component-level circuit cannot yet be completed from the public summary.

## Result

A 66 × 138 mm main board is realistic if the design stops using large breakout
boards and 2.54 mm headers. The base handset can retain the requested features,
but cellular voice must pass a separate module/carrier acceptance gate before
the schematic is frozen.

The selected architecture is:

- retained ESP32-S3-WROOM-1-N16R8 plus component-down SX1262, CC1101, GNSS,
  NFC, LF RFID, keypad scanner,
  charger/power path, fuel gauge, and regulators on the main PCB;
- MakerFocus 3000 mAh protected pouch below the keypad region;
- 2.4-inch capacitive-touch LCD instead of the current 3.5-inch Waveshare panel;
- cellular module on the main PCB if its US voice variant is accepted, with the
  rear pod retained for optional NFC/RFID coils or other expansion hardware;
- separate antennas/keepouts for Wi-Fi/BLE, LTE, LoRa, CC1101, GNSS, NFC, and
  125 kHz RFID. Small IC packages do not make the antennas disappear.

## Recommended candidates

| Function | Existing implementation | Compact candidate | Package / envelope | Decision |
|---|---|---|---|---|
| MCU, Wi-Fi, BLE, PSRAM | ESP32-S3-WROOM-1-N16R8, 18 × 25.5 mm | **Retain ESP32-S3-WROOM-1-N16R8** | 18 × 25.5 mm module | Selected by the user. Preserve the current 16 MB flash and 8 MB PSRAM configuration and its required antenna keepout. The smaller PICO proposal is rejected for this revision. |
| LTE data and voice | 44.45 × 31.75 × 12.44 mm A7670E carrier | SIMCom A7672G | 24 × 24 × 2.4 mm LCC/LGA | Best functional-size candidate: global/US bands, VoLTE, analog audio, SIM and direct 3.4–4.2 V supply. Carrier approval for the exact US operator is still a hard gate. |
| LTE carrier-approved fallback | unresolved | SIMCom SIM7672G / SIM7672NA | 24 × 24 × 2.4 mm LCC/LGA | SIM7672G has an AT&T certificate listed by SIMCom and NA bands are available, but the public product table lists PCM and does not establish analog audio/VoLTE. Do not substitute it until voice is confirmed on the exact firmware/operator. |
| LoRa / Meshtastic | 17 × 16 × 3.2 mm Ra-01SH module | Semtech SX1262 | 4 × 4 mm QFN | Use component-down with Semtech's 915 MHz reference RF network, TCXO/crystal choice, RF switch policy, controlled-impedance feed, and U.FL or validated antenna. |
| CC1101 sniff/replay | roughly 17 × 16 mm header module | TI CC1101 | 4 × 4 × 1 mm VQFN | Use the TI 868/915 MHz reference layout and matching network. Keep it on its own RF feed and antenna; it cannot share an unmatched LoRa path. |
| GNSS and PPS | u-blox MAX-M10S, 9.7 × 10.1 × 2.5 mm | u-blox UBX-M10050-KB | 4 × 4 × 0.55 mm QFN | Smallest credible same-family choice. It adds a 1.8 V rail, timing source, RF filtering/matching, backup supply decisions, and tighter RF layout. Keep MAX-M10S if schedule/risk matters more than about 80 mm². |
| NFC reader/writer | PN532 breakout, about 40 × 40 mm | ST ST25R3916B-AQET | 5 × 5 × 0.55 mm QFN | Component-down reader with a flex or case-mounted 13.56 MHz loop. The loop and matching network dominate mechanical area. This is not pin/firmware compatible with PN532. |
| 125 kHz RFID reader | RDM6300 breakout, about 38 × 22 × 8 mm | NXP HTRC110 or EM Micro EM4095 | HTRC110 SO14 about 8.7 × 3.9 mm body; EM4095 SO16 about 9.9 × 3.9 mm body | HTRC110 is the first candidate for HITAG/compatible AM/PM tags; EM4095 has a broader documented 100–150 kHz AFE. Both still require a large tuned coil and analog validation. |
| 4×4 keypad scan | PCF8574 plus 16 SOD-123 diodes | TI TCA8418 | 4 × 4 mm WQFN | Preferred. It scans/debounces up to 80 keys, provides FIFO and interrupt, and removes the expander/diode sprawl. Arbitrary multi-key rollover/ghost behavior must be tested; retain tiny per-key diodes if chorded keys are required. |
| Battery charger and power path | TP4056 plus incomplete protection/path | TI BQ25185 | 2.2 × 2.0 mm WSON | Preferred charger front end: 1 A, input current limiting, thermistor input, and system power path. It does not excuse protection validation; use the protected pack and add a designed secondary protection policy if required. |
| Battery gauge | MAX17048 breakout/header | MAX17048G+T | 2 × 2 mm TDFN | Keep the IC, remove the breakout/header. WLP is smaller but TDFN is friendlier for prototype assembly. |
| 3.3 V system rail | undefined LDO | TI TPS63802 | 3 × 2 mm VSON-HR; 21.5 mm² reference solution | Preferred 2 A buck-boost so 3.3 V stays regulated across the full LiPo range. The RF/display peak-load budget still needs calculation. |
| Low-current 1.8 V rail | none | TI TPS62840 | SON or WCSP; up to 750 mA | Suitable candidate for GNSS/digital 1.8 V loads. Do not use it for LTE. |
| 5 V rail | TPS61023 used as modem boost | TPS61023 only for RFID/audio loads that truly need 5 V | 1.6 × 1.6 mm SOT-5X3 | Remove the always-on modem 5 V architecture. A7672-class modules use 3.4–4.2 V directly from the protected cell. Switch a small 5 V domain only for confirmed loads. |
| Speaker output | external/unfinished analog path | modem analog audio, or MAX98357A for ESP32 media audio | 1.345 × 1.435 mm WLP or 3 × 3 mm QFN | A7672 analog audio is simplest for calls. MAX98357A adds compact I²S media/key-tone output but does not by itself connect a modem call path. |
| Microphone | electret harness | low-profile analog MEMS for modem; optional Knowles SPH0645 for ESP32 I²S | SPH0645 is 3.5 × 2.65 × 0.98 mm | Keep the call microphone electrically compatible with the chosen modem. A digital I²S mic is optional for recorder/assistant features. |
| microSD | header/module | Molex 504077-1891 or retained exact socket | 1.28 mm high | Use a real side-access socket on the PCB; no breakout. |
| nano-SIM | JAE SF72S006 | retain SF72 or use SF70 tray | SF72 11.2 × 14.3 × 1.25 mm | Already compact. SF70 is preferable for a sealed-looking side tray but slightly larger. Connect it only to the selected modem's SIM interface. |
| USB-C data/charge | GCT USB4105 | retain USB4105 | 7.35 mm body, 3.31 mm profile | Already compact and mechanically robust for its size. Keep USB 2.0 D+/D−, CC resistors, ESD and input protection. |
| Display/touch | Waveshare 3.5-inch, 61 × 92.44 mm | EastRising ER-TFT024IPS-3 with capacitive touch option | 42.72 × 59.26 × 2.3 mm before final touch-stack drawing | Rotate to landscape. Its 48.96 × 36.72 mm active area fits the reference proportions. Freeze the exact capacitive-touch ordering code and FPC drawing before schematic/layout. |
| Trackball | Pimoroni PIM447, 25 × 22 × 11 mm | retain PIM447 initially | 25 × 22 × 11 mm | No manufacturer schematic for safely cloning its Nuvoton/Hall-sensor circuit was found. Recess its board through a main-PCB cutout. A custom raw-trackball circuit is a separate reverse-engineering project. |
| IR transmit/receive | mismatched TSAL6200 value/0805 footprint and TSOP header | real top-facing IR LED + receiver with transistor driver | mechanical part choice pending | Fix the electrical driver and footprint first. Shrinking the emitter can materially reduce usable range, so package size alone should not choose it. |

## Cellular decision gate

Cellular is the one part that cannot be selected from package size alone.

### Candidate A: A7672G

SIMCom specifies a 24 × 24 × 2.4 mm module, 3.4–4.2 V supply, global/US LTE
bands including B2/B4/B5/B12/B13/B17/B25/B26/B66, VoLTE, analog audio, UART,
USB, SIM interface, and optional GNSS. It is the closest compact replacement for
the intended data/calling function.

Before committing it, obtain the current hardware design guide and exact module
ordering code, then verify:

1. AT&T/T-Mobile/Verizon acceptance for that exact hardware and firmware;
2. VoLTE provisioning and a successful call using the intended SIM/account;
3. analog microphone/speaker reference circuit and audio levels;
4. peak current waveform, required local bulk capacitance, and allowable battery
   drop from the MakerFocus pack/protection board;
5. LTE antenna, RF connector, ground keepout, coexistence, SAR, and certification.

### Candidate B: SIM7672G or SIM7672NA

These use the same 24 × 24 × 2.4 mm class of package. SIMCom lists Cat-1 bis,
US bands, PCM, SIM/UART/USB and an AT&T certificate for SIM7672G. Its public
summary does not prove the analog voice path or VoLTE behavior needed here.
It is a strong data-first fallback, not yet an approved phone modem.

### Integration recommendation

Reserve a compatible 24 × 24 mm modem zone on the upper rear of the new PCB,
connected to the protected battery through a rated load switch/current path and
local low-ESR bulk capacitance. Direct battery operation will stop using LTE once
the cell falls below the modem's 3.4 V minimum; decide whether that reduced usable
capacity is acceptable or add a modem-rated 3.8 V buck-boost after measuring the
real peak waveform. Keep the detachable pod option in the
mechanical design until bench tests prove the modem, heat, antenna and audio.
The PCB should support a no-modem build without breaking the mesh/GPS handset.

## What actually gets smaller

Package/body area comparison is only a rough indicator; it excludes passives,
connectors, keepouts and antennas.

| Block | Old body/module area | Compact IC/module area | Approximate body-area reduction |
|---|---:|---:|---:|
| ESP32 module | 459 mm² | 459 mm² | 0% — current N16R8 module retained |
| LTE carrier | 1411 mm² | 576 mm² | 59% |
| LoRa module | 272 mm² | 16 mm² | 94% |
| CC1101 module | 272 mm² | 16 mm² | 94% |
| GNSS module | 98 mm² | 16 mm² | 84% |
| PN532 breakout | 1600 mm² | 25 mm² | 98% before antenna |
| RDM6300 board | 836 mm² | about 34–39 mm² | about 95% before coil |

The antenna/coil zones remain the limiting geometry. NFC and LF RFID especially
need case-mounted coils. LTE, GNSS, Wi-Fi/BLE, LoRa and CC1101 should use separate
RF connectors or validated antennas during bring-up rather than one improvised
shared antenna network.

## Proposed board partition

The 66 × 138 mm board should be partitioned before detailed placement:

- top 30–35 mm: LTE, GNSS, RF connectors and antenna keepouts;
- display region: low-profile MCU, memory, LCD FPC and touch circuitry, avoiding
  copper/parts under any display area prohibited by the panel drawing;
- trackball aperture: PIM447 recessed through a board cutout, with no tall parts
  in its mechanical sweep;
- keypad region: sixteen switches plus TCA8418, with the battery beneath;
- edge strip: USB-C, power switch, microSD, SIM tray, IR devices and ESD;
- rear-flex interfaces: NFC loop, LF RFID coil, speaker, microphone and expansion.

Do not place LTE, GNSS, Wi-Fi/BLE, LoRa and CC1101 antennas together at the top
without a coexistence plan. The board outline may fit while the RF product fails.

## Recommended first prototype scope

Freeze these parts first because they define routing, power and mechanics:

1. 2.4-inch display ordering code and FPC pinout;
2. A7672G versus a carrier-approved voice-capable fallback;
3. placement and antenna keepout for the retained ESP32-S3-WROOM-1-N16R8;
4. main-board LTE versus detachable LTE pod after a paper placement study;
5. NFC and LF RFID coil locations and whether they are base features or plug-in
   rear modules;
6. antenna count, connector type and enclosure keepouts;
7. complete battery/charger/protection/current budget.

Then build a radio/power test PCB before committing the handset PCB. It should
exercise LTE calls/data, both sub-GHz radios, GNSS, USB and the exact battery
power path under simultaneous peak loads.

## Primary sources

- [ESP32-S3-WROOM-1 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
- [SIMCom A7672G](https://www.simcom.com/product/A7672G.html)
- [SIMCom SIM7672 series](https://en.simcom.com/product/SIM7672.html)
- [SIM7672G AT&T certificate listing](https://en.simcom.com/technical_files-p2.html?filetype=0&pro_cat=4&pro_li=157&time=0)
- [Semtech SX1262](https://www.semtech.com/products/wireless-rf/lora-connect/sx1262)
- [TI CC1101](https://www.ti.com/product/CC1101)
- [u-blox UBX-M10 series](https://www.u-blox.com/en/product/ubx-m10-series)
- [u-blox MAX-M10S datasheet](https://content.u-blox.com/sites/default/files/MAX-M10S_DataSheet_UBX-20035208.pdf)
- [ST ST25R3916B](https://www.st.com/en/nfc/st25r3916b.html)
- [NXP HTRC110](https://www.nxp.com/products/rfid-nfc/hitag-lf/hitag-reader-solution%3AHTRC11001T)
- [EM Microelectronic EM4095](https://www.emmicroelectronic.com/product/rf-reader-ics/em4095)
- [TI TCA8418](https://www.ti.com/product/TCA8418)
- [TI BQ25185](https://www.ti.com/product/BQ25185)
- [Analog Devices MAX17048](https://www.analog.com/en/products/max17048.html)
- [TI TPS63802](https://www.ti.com/product/TPS63802)
- [TI TPS62840](https://www.ti.com/product/TPS62840)
- [TI TPS61023](https://www.ti.com/product/TPS61023)
- [Analog Devices MAX98357A](https://www.analog.com/en/products/max98357a.html)
- [EastRising ER-TFT024IPS-3](https://www.buydisplay.com/2-4-inch-ips-240x320-tft-lcd-display-capacitive-touch-screen)
- [Molex 504077 microSD connector](https://www.content.molex.com/dxdam/literature/987650-7752.pdf)
- [JAE SF70/SF72 nano-SIM connectors](https://www.jae.com/releases/detail/id%3D1689)
- [GCT USB4105](https://gct.co/connector/usb4105)
