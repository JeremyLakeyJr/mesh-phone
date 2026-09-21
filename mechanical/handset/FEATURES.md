# Feature preservation contract — new handset

All entries below remain requirements. “Reserved” means space/interface intent,
not completed routing, measured coexistence or working firmware. This new case
must not be treated as proof that the full electronics fit or function.

| Feature retained | New physical provision | Required implementation / limit |
|---|---|---|
| ESP32-S3, Wi-Fi, BLE, PSRAM | New main board, upper electronics region | Preserve N16R8 allocation; reserve manufacturer antenna keepout, not just package outline |
| Color capacitive touchscreen | Upper opening and location ribs | EastRising ER-TFT024IPS-3 is the research lead: 240×320 IPS/ST7789, rotated landscape in a provisional 60.5 × 43.5 × 3.5 mm CTP envelope; freeze exact ordering code/FPC |
| PIM447 trackball and click | Centered circular opening and proposed 27 × 24 mm PCB cutout | Preserve I²C/interrupt and 25 × 22 × 11 mm carrier; add measured carrier retention |
| 4×4 keypad / expander | Sixteen rectangular retained caps | Relocate all sixteen switches and diode matrix; preserve expander/control signals |
| MakerFocus 3000 mAh battery | Lower rear cradle, strap and lead exit | 67 × 38 × 12 mm tolerance envelope; confirm actual plug/polarity and clear solder joints |
| Charging, protection, fuel gauge | Main-board power region, USB-C access | Preserve function; existing power/protection/gauge circuits still require redesign |
| USB-C charging and data | Right-side opening | Preserve both data and charging; new connector position and ESD/CC design |
| Physical power switch | Left-side opening | Preserve earlier user placement preference; new board footprint alignment |
| LTE calls / SMS / data | Detachable rear carrier pod, dedicated harness and SIM aperture | Separate high-current power plus UART/control/analog audio; US modem still unresolved; handset LTE unavailable without pod |
| Speaker / microphone | Upper-left speaker vents, bottom front mic hole | Reserve low-profile speaker in upper rear, mic in front lower region; final parts and acoustic retention required |
| SIM | Pod right-side slot | Use the selected modem's own SIM supply/socket; relocate slot to measured carrier, do not parallel host SIM |
| microSD storage | Right-side slot near middle | New board socket alignment and measured eject clearance required |
| SX1262 / Ra-01SH 915 MHz | Main board upper RF region | Retain 17 × 16 × 3.2 mm module, RF switch/control signals and antenna connection |
| CC1101 radio | Separate main-board RF region | Retain module/interface and independent antenna routing |
| Meshtastic / Reticulum intent | ESP32 and LoRa retained | Firmware support is a requirement, not implemented by the case |
| MAX-M10S GPS / PPS | Upper rear main-board region | Retain UART/PPS/passive-antenna connector; antenna needs dedicated clear plastic area and RF tests |
| IR transmit / receive | Two 6 mm top-facing apertures | Measured LED/receiver carrier, transmitter driver and receiver GPIO still required |
| NFC / PN532 | Optional external module housing through accessory path | Preserve daughterboard and antenna/coil; don't assume 40 × 40 mm breakout fits beside LTE inside the same pod |
| 125 kHz RFID / RDM6300 | Optional external module housing and remote coil | Preserve 38 × 22 × 8 mm board allowance; requires 5 V and validated logic levels |
| External module slot / J16 | Separate rear 18 × 8 mm opening, pod side cable exit | Existing keyed cable interface retained as baseline; NOT a blind-mate card slot |
| Concurrent LTE + expansion | Independent modem and accessory harness openings | LTE does not consume J16; power/interface design for simultaneous loads remains required |
| Removable external modules | Recessed cover, asymmetric locator, M2-retained pod | Power off/unplug USB before swaps; connector must not bear mechanical loads |
| Boot/reset service | Case removable via four screws | Preserve buttons on new board; access after removing front |

The existing J16 contract is 3.3 V with a **50 mA** usable budget pending supply
redesign. It cannot power the modem and is not assumed adequate for PN532 or
5 V RFID. Keeping those features means carrying their existing dedicated
power/signal interfaces forward or explicitly designing an upgraded accessory
interface. No silent pin substitution, voltage change or back-powering is allowed.

The old design deliberately removed the camera. It remains excluded. Exact
screen size is the one intentional user-interface hardware change needed for
the supplied reference proportions; touch, trackball and all sixteen keys remain.

Full-feature portability must be judged with the required accessories attached:
the base is 26 mm thick, LTE pod adds 16.8 mm locally, and optional NFC/RFID
hardware adds its own volume. A truly 26 mm all-in-one version requires integrated
radio/modem/coil hardware beyond this mechanical concept.
