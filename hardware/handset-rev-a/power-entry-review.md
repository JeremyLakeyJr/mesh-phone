# Battery and USB input revision — 23 September 2026

**Engineering work in progress. DO NOT FABRICATE OR POWER.**

This revision replaces the fixed BQ25185 charger with the pin-compatible-package
but electrically different **BQ25186DLHR**. The former 300 mA charge setting and
six-hour timeout could not fully charge a 3000 mAh pack: even an ideal constant
300 mA takes ten hours, before taper or system load. The new circuit requires
firmware configuration and defaults to hardware-disabled charging.

## Circuit and parts

USB1 VBUS → F1 → USB_FUSED → U21 TPS25200 → USB_PROTECTED → U3 IN.
D1 SMF5.0A clamps the fused input. U23 TLV70433 supplies U22 TUSB320LAI from
USB_FUSED, independently of the battery/host, so Type-C source detection can
start with a discharged pack. U22 is sink-only in GPIO mode, with internal Rd;
the old external CC pulldowns R8/R9 have been repurposed, not left in parallel.
USB data remains with the ESP32 and existing U17 protection; data routing remains.

U22 OUT1 goes low for 1.5 A or 3 A advertisement. Q6 AO3401A converts that into
USB_CC_AUTO; D2 BAT54C ORs it with the separately authorized USB_LEGACY_EN.
R67 pulls the eFuse enable low otherwise. Q7 AO3400A provides isolated open-drain
source-status sensing into the main rail, avoiding an always-on USB signal
driving an unpowered expander input. U24 TCA9536 adds control/status on the
existing I2C bus (0x41); U3 uses 0x6A. No ESP32 GPIO has been reassigned.

U24 P0 drives Q5 to pull U3 CE low. R6 pulls CE high to VSYS by default;
R7 and R68 are 4.7 kΩ pulldowns that dominate the expander's approximately
100 kΩ startup pullups. P1 authorizes legacy input; P2 senses Type-C current
permission and P3 senses the eFuse's open-drain fault. Both status nets have
10 kΩ pullups to the main 3.3 V rail.

F2 sits between J1 positive and every VBAT load. F1/F2 are Littelfuse
046701.5NRHF 1.5 A fuses. They provide fault protection, **not** a precision
1.5 A operating-current ceiling or reverse-polarity protection. Connector polarity
and the purchased pack's protection still require physical verification.
J2 remains a real external 10 kΩ B3435 thermistor attached to the battery.

R65=100 kΩ, 1% sets the TPS25200 to approximately 0.97 A typical; resistor
tolerance and the datasheet limit envelope must be included in qualification.
The eFuse is not a USB 500 mA source limiter. U3's configured input-current limit
sets the normal permitted draw. USB detector/LDO current also consumes source
budget. The TVS/eFuse arrangement is not a claim of continuous high-voltage
input survival: fuse clearing, TVS pulse energy, hot-plug and fault coordination
must be tested.

## Charging and USB policy

[charger-policy.json](charger-policy.json) is the register contract, checked by
`python3 scripts/check_handset_charger_policy.py`. It is **not running firmware**.

| Source | Charger input limit | Requested charge | Permission |
|---|---:|---:|---|
| Unknown, detached or fault | 100 mA fallback | Disabled | Legacy input off; CE off |
| Enumerated/configured legacy host granting 500 mA | 400 mA | 300 mA | Explicit USB-stack authorization; revoke on suspend/reset/detach |
| Type-C advertising 1.5 A or 3 A | 665 mA | 500 mA | Hardware CC qualification; keep legacy override off |

Common settings: 4.18 V nominal cell target, 12-hour fast-charge timer with
2× slowing under limiting conditions, 160-second hardware-reset watchdog,
80 °C die thermal regulation, DPPM enabled, nominal 5–45 °C charging window
with cool-region current derating. Cell voltage and thermistor tolerances still
need assessment. Charge current will fall below the requested value when
input power, temperature or system demand requires it.

Preload expander outputs low before changing their direction. Configure/read
back all charger limits while CE remains off. Check VIN-good and faults before
enabling charge. Latch safety-timer faults; never repeatedly restart charging
to bypass a timeout. An I2C error must request shutdown and latch a fault, but
cannot guarantee immediate GPIO deassertion on a failed bus. Bench-test that
watchdog SYS reset collapses the main rail and resets the expander/CE gate.

**Known product limitations:** no BC1.2 detector or USB PD negotiation; depleted
pack startup requires a Type-C source advertising 1.5 A or 3 A. Legacy USB
authorization needs a running battery-powered host. SW19 off removes host/
expander power, so powered-off charging is not implemented. These are outstanding
product requirements, not features silently removed from the final handset.

The MakerFocus 103665 listing specifies approximately **1.5 A maximum operating
current**. U20's modem converter draws directly from fused VBAT and bypasses the
charger's discharge limiter. Modem bursts plus handset load can exceed the pack
rating. The battery/modem power budget remains a release blocker; a fuse does
not solve it. The selected 500 mA charging request is below the listing's
0.2C/600 mA standard charge figure, subject to exact-pack verification.

## Layout and verification scope

The power-entry revision is installed in the saved project after native
DRC/parity, physical continuity and source-hash checks. Its previous revision
is preserved at `archive/handset-before-power-entry/e4248d73f7a3/`.
The 113 local pads pass continuity. The checker excludes external 3.3 V,
VSYS and I2C distribution and USB data pairs.
Those connections remain essential before this circuit can function.

Local geometry is not electrical or thermal qualification. Filled/capped
via-in-pad assembly review, capacitor effective capacitance, exact passive MPNs,
charge thermal dissipation, protection coordination, pack polarity, NTC attachment,
firmware and fault-injection tests remain required. The complete handset release
gate remains closed regardless of local routing progress.

## Primary references

- [TI BQ25186 datasheet](https://www.ti.com/lit/ds/symlink/bq25186.pdf), pinout and register map.
- [TI TPS25200 datasheet](https://www.ti.com/lit/ds/symlink/tps25200.pdf), pinout, clamps and current-limit equations.
- [TI TUSB320LAI datasheet](https://www.ti.com/lit/ds/symlink/tusb320lai.pdf), sink configuration and GPIO current-advertisement truth table.
- [TI TLV704 datasheet](https://www.ti.com/lit/ds/symlink/tlv704.pdf), DBV pinout, supply range and capacitor requirements.
- [TI TCA9536 datasheet](https://www.ti.com/lit/ds/symlink/tca9536.pdf), startup direction/pullups and register ordering.
- [AOS AO3401A](https://www.aosmd.com/sites/default/files/res/datasheets/AO3401A.pdf), low-voltage P-channel switch.
- [AOS AO3400A](https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf), N-channel gates/status isolation.
- [Nexperia BAT54C](https://assets.nexperia.com/documents/data-sheet/BAT54C.pdf), common-cathode diode OR.
- [Diotec SMF5.0A](https://diotec.com/files/diotec/productfiles/datasheet/smf50a.pdf), polarity and pulse ratings.
- [Littelfuse 467 series](https://www.littelfuse.com/assetdocs/fuse-467-datasheet?assetguid=4a59f034-1cca-460e-a5ba-e1e66247c76d), fuse clearing and ratings.
- [MakerFocus 3000 mAh pack](https://www.makerfocus.com/products/makerfocus-3-7v-3000mah-lithium-rechargeable-battery-1s-3c-lipo-battery-pack-of-4), dimensions, connectors and published charge/discharge limits.
