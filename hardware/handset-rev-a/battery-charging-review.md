# Battery and charging review — 2026-09-25

**Open engineering blocker. Do not fabricate or power.** Published-pack research,
a voltage-margin correction, a budget screening tool and a portable controller
are complete. Physical pack verification, STM32 supervisor integration, powered-off charging,
external power/I2C routing and bench qualification are not complete.

## Pack identification and limits

The user's 3.7V / 3000mAh / 11.1Wh description matches the MakerFocus listing
linked in `battery-qualification.json`; nominal energy is 3.7 × 3 = 11.1Wh.
The listing identifies a 103665 protected pouch. Both connector variants are
sold, so capacity/energy alone cannot identify the actual mating connector or
positive cavity. Do not assume a JST family or polarity from wire colors.

The design retains the 67 × 38 × 12mm tolerance envelope. Record actual size,
connector part number and mating-face polarity before wiring J1. Obtain a
consistent cell/protection specification: the marketing C-ratings and charging
instructions are contradictory. Screening uses the explicit 1.5A operating
limit, not the advertised 3C. Published protection trip limits are not an
allowable continuous load or a substitute for system current control.

## Voltage and charge policy

Changed VBAT_CTRL from 0x44 (4.18V) to **0x43 (4.17V)**. With the datasheet's
+0.5% regulation accuracy, the old setting could reach 4.2009V; the new setting
reaches 4.19085V. This is a regulation-tolerance calculation, not proof of all
transients or a qualified cell voltage limit. Do not adopt the listing's
contradictory 4.25V charging text.

Current requests remain 300mA with configured legacy USB permission and 500mA
with Type-C 1.5A/3A advertisement. These are nominal settings; charge-current
accuracy, input headroom, temperatures and exact cell limits must still be
included in acceptance testing. No firmware or bench result is inferred from
register encodings alone.

## Power-budget decision

`check_handset_battery.py` produces `battery-budget-report.json`. Its deliberately
labelled **illustrative** case assumes 3.0V battery, 3.792V/2.0A modem output,
85% converter efficiency and 0.25A other battery demand. It requires 3.2241A
from the pack. Under those assumptions, the 1.5A operating limit would leave
only 0.8406A at the modem output. These are not a selected modem's measured
requirements or an enforceable current limit.

The existing F2 fuse and charger discharge limiter cannot make this scenario
compatible: the modem converter is fed directly from fused VBAT. Do not enable
full-power LTE until a specific adapter's worst-case burst/current profile and
all simultaneous handset loads fit a verified source budget. Resolve this by
qualifying a lower-demand adapter, giving the modem an independently qualified
power source, or approving a suitably rated pack. Do not silently substitute a
battery, throttle undocumented modem behavior or rely on the protection trip.

## Temperature sensing

J2 must connect to an actual 10kΩ B3435 NTC thermally coupled to the pouch;
no fixed-resistor bypass. The existing nominal 5–45°C charging window is not
proof of the purchased cell's temperature rating. Select the exact thermistor
MPN and include resistance/B-value tolerance, charger threshold accuracy and
sensor lag. Secure it against the pouch with an electrically insulating,
cell-compatible attachment; avoid sharp edges, tabs and local charger heat.
Verify cold/hot transitions, open/short sensor response and worst-case warming
on the assembled device. Attachment and temperature limits remain unverified.

## Controller implementation and recovery

See [firmware integration](../../firmware/power/README.md). The new portable
C++17 controller implements the current register policy, checks readback,
preloads GPIO outputs low, distinguishes CC from legacy USB authorization,
waits for input power-good, and latches faults. It does not repeatedly toggle
CE during steady operation. A durable session marker prevents charging from
silently resuming after reset. Explicit service review is required to rearm;
a detailed persistent fault-reason log is still an integration requirement.

Host tests passed with strict compiler warnings and UndefinedBehaviorSanitizer,
including every startup/enable write failure. The policy checker also verifies
the controller's common-register constants. No ESP32 executable, I2C HAL,
USB event integration, NVS implementation or hardware test is claimed.

## Powered-off charging and remaining routing

The user selected a separate supervisor. The STM32G031 always-on circuit and
isolated host interface are now captured and placed; see
[power-supervisor-review.md](power-supervisor-review.md) for exact pin assignments,
checks and unresolved reset-time charge-inhibit requirements. U24 and its status
pull-ups now use PWR_AON_3V0; U3/U24 have a private supervisor bus. SW19 continues
to control the main handset rail.

This is circuit capture, not working powered-off charging. Routing, STM32
firmware, legacy host-permission expiry, depleted-pack recovery and hardware
qualification remain open. The prior 113-pad continuity result covers only the
existing local power-entry cell.

Sources: [MakerFocus pack listing](https://www.makerfocus.com/products/makerfocus-3-7v-3000mah-lithium-rechargeable-battery-1s-3c-lipo-battery-pack-of-4),
[TI BQ25186 datasheet](https://www.ti.com/lit/ds/symlink/bq25186.pdf), and
[TCA9536 datasheet](https://www.ti.com/lit/ds/symlink/tca9536.pdf).
