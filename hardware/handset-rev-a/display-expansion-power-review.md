# Display and expansion power review — 2026-09-27

**Historical resistor update (superseded 2026-10-01):** R52–R55 now specify **Vishay CRCW0603150RFKEAHP**, 150 Ω ±1%, in the existing 0603 footprints. The schematic and PCB contain explicit MPN fields; the connectivity specification, placement table and `generated/backlight-resistor-bom.csv` agree. Resistance, nets, component placement and copper geometry are unchanged.

The [current Vishay CRCW-HP e3 datasheet](https://www.vishay.com/docs/20043/crcwhpe3.pdf), revision 17-Mar-2026, specifies 0.33 W P70 for the 0603 part. It makes that rating conditional on permissible film temperature and assembly thermal performance. This replaces the previous 0.1 W specification; it is not a completed thermal qualification.

The CAT4004A driver now replaces Q2 and R52–R55; see the [backlight implementation and routing review](backlight-routing-review.md) for current topology, evidence and remaining limits. The resistor calculations below document the previous design.

## Display findings

[EastRising's ER-TFT024IPS-3 datasheet](https://www.buydisplay.com/download/manual/ER-TFT024IPS-3_Datasheet.pdf), page 11, specifies VCI 2.5–3.3 V, VDDI 1.65–3.3 V, backlight current 70 mA typical/80 mA maximum, and LED Vf 3.2 V typical/3.4 V maximum at the stated test current. It supplies no minimum LED Vf. Direct PDF retrieval returned 403; these table values were available through the indexed manufacturer PDF. The [manufacturer product page](https://www.buydisplay.com/2-4-inch-ips-240x320-tft-lcd-display-capacitive-touch-screen) corroborates the part, 2.8 V typical supply and 70 mA typical backlight. Exact purchased touch configuration and complete panel documentation remain qualification requirements.

- **Supply conflict:** R31/R32 plus the [TPS63802](https://www.ti.com/lit/ds/symlink/tps63802.pdf) PWM reference accuracy produce a 3.212–3.390 V reference/resistor corner range. The previous J26 topology tied its supplies to that rail; the dedicated supply and translation are now captured and placed in the [display interface update](display-interface-review.md), with routing completed in the [routing review](display-routing-review.md) and electrical qualification pending. The upper corner exceeds the recommended 3.3 V maximum, before feedback leakage, ripple or transients. The panel's higher absolute-maximum voltage is not an operating target. Resolve dedicated display supply and I/O-level compatibility before extending its power routing; do not simply lower one supply while leaving incompatible I/O levels.
- **Backlight reference case:** the [TPS61023](https://www.ti.com/lit/ds/symlink/tps61023.pdf) PWM reference and installed R34/R35 give 4.9504 V nominal and a 4.742–5.165 V reference/resistor corner range. Using 3.2 V LED Vf and zero MOSFET drop estimates 11.67 mA per branch, 46.68 mA total. This is not a self-consistent LED-curve solution or guaranteed brightness/current bound: the published Vf is measured at a different current and minimum Vf is absent.
- **Resistor fault case:** with zero LED Vf, the upper calculated rail corner and minimum resistor value give about 34.78 mA and **0.180 W per branch**. That exceeds the old 0.1 W requirement. The specified high-power replacement has nominal rating margin, but assembly temperature, TCR, leakage/ripple and fault duration still require verification. It does not protect the LED from excessive current or provide constant-current regulation.

## Expansion findings

Using [TI TPS2553](https://www.ti.com/lit/ds/symlink/tps2553.pdf), section 9.5.1, and R41 = 100 kΩ ±1%, the current-limit equations give approximately **232.0 mA minimum, 266.3 mA nominal and 305.8 mA maximum**. This is a switch limit, not an accessory's normal demand, a 500 mA port rating, or a guarantee of startup into arbitrary capacitance. The resistor tolerance is included; routing effects and hardware qualification remain open.

U14 EN remains tied to +3V3. EXP_FAULT_N is not connected to host monitoring. Independently controlled enable, fault reporting, startup capacitance, signal back-power behavior and an enforceable module power allowance remain necessary before using port shutdown as part of a power budget.

## Checks and next step

`check_handset_display_expansion.py` verifies the relevant netlist/specification contracts, resistor tolerances and explicit high-power MPN. Its findings are recomputed by the manufacturing-release gate. Four regression tests cover ILIM tolerance, the former resistor-rating failure, invalid resistor values and missing panel evidence. Geometry-preservation checks pass; native DRC retains the four inherited USB1 hole-clearance findings, zero schematic parity findings and 393 unconnected items. Checkpoint: `archive/handset-before-backlight-resistors/521d0573b5d8/`.

Next: electrically qualify the routed dedicated display supply/I/O arrangement and resolve backlight current regulation, then add expansion enable/fault control. Keep display logic/touch and accessory current profiles unqualified until measured or bounded by applicable specifications. **DO NOT FABRICATE OR POWER.**
