# Dedicated display domain — 2026-09-27

**Capture milestone (2026-09-27).** Physical routing is now installed and checked in the [display routing update](display-routing-review.md); electrical qualification remains open. Twelve specified parts replace the direct host-to-panel connections with a dedicated supply and translated signals. The external 2.4-inch display, capacitive-touch interface and existing backlight circuit are retained. See `generated/display-interface.kicad_sch` and `generated/display-interface-bom.csv`.

| Part | Selected MPN | Function |
| --- | --- | --- |
| U28 | TPS7A2030PDBVR | 3.0 V LCD_3V0 regulator from +5V_RF, enabled by SYS_EN |
| U29 | SN74LVC244APWR | Six host-to-panel signals, powered by LCD_3V0 |
| U30 | SN74LVC2G125DCUR | Panel MISO and touch IRQ return to host, powered by +3V3 |
| U31 | TCA9406DCUR | Bidirectional touch I²C translation |
| C84–C85 | GRM188R61E475KE11D | Regulator input/output capacitors, 4.7 µF |
| C86–C89 | GRM155R71C104KA88D | Buffer/translator supply bypass, 100 nF |
| R80–R81 | RC0402FR-07100KL | Panel MISO pulldown and touch IRQ pullup, 100 kΩ |

## Supply and interface reasoning

The [TPS7A20 datasheet](https://www.ti.com/lit/ds/symlink/tps7a20.pdf) specifies ±1.5% output accuracy: the selected 3.0 V part gives **2.955–3.045 V in regulation**, inside the panel's recommended supply range. The 5 V source provides headroom; its previously calculated 5.165 V upper reference/resistor corner is below the regulator's 6 V recommended input maximum. This does not qualify ripple or transients. DBV pins are IN=1, GND=2, EN=3, NC=4, OUT=5. Require at least 1 µF effective output capacitance after DC bias and temperature. Its 300 mA capability is a component limit, not an approved display load. Dissipation is approximately `(VIN−3.0)*ILOAD`: about 0.20 W at 5 V/100 mA; PCB thermal performance must set the actual limit.

J26 supply/strap pins 7, 8, 9, 35, 40, 41 and 42 and C47/C48 now use LCD_3V0. J26 backlight power stays on +5V_RF. The whole logic/touch load now draws from the 5 V branch through an LDO: count approximately the same current plus regulator quiescent current at its input, not lossless voltage-ratio scaling. `system-power-inputs.json` records this change and keeps consumption unknown.

[SN74LVC244A](https://www.ti.com/lit/ds/symlink/sn74lvc244a.pdf) U29 uses 3.3 V tolerant inputs and LCD_3V0-referenced outputs for clock, MOSI, chip select, display command/reset and touch reset. Both active-low enables are grounded. Unused inputs are grounded; unused outputs are explicitly unconnected. The PW/TSSOP pin table was used, not the different RWP arrangement.

[SN74LVC2G125](https://www.ti.com/lit/ds/symlink/sn74lvc2g125.pdf) U30 translates the two return signals. **MISO output enable follows host LCD_CS** so deselection releases the shared SPI bus; existing R58 pulls LCD_CS high. R80 defines the panel-side input when the panel releases it. The second channel returns touch IRQ and stays enabled; R81 pulls its input to the panel rail. These LVC devices support partial-power-down Ioff. That feature does not establish system startup/shutdown correctness or timing closure.

[TCA9406](https://www.ti.com/lit/ds/symlink/tca9406.pdf) U31 uses A=LCD_3V0, B=+3V3 and OE tied to VCCA, as permitted for an enabled interface. Its internal 10 kΩ pullups must be included alongside existing host pullups when checking sink current and rise time. VCCA≤VCCB is satisfied at the calculated steady-state corners; power sequencing still requires verification. Cable capacitance, clock stretching, transition acceleration and the purchased touch controller's actual electrical limits remain open.

## Verification at the capture milestone

- 250 components; **2,298/2,298 artifact integrity checks** pass.
- Native schematic/PCB parity: **zero** findings.
- ERC: unchanged **30** findings (24 isolated labels, six undriven power pins).
- DRC: unchanged **four inherited USB1 hole-clearance findings**; no new placement violations.
- **433 unconnected items**, up from 393 because the new circuit is not routed. Ground-plane refill also changes connectivity counts.
- Existing footprints and trace/via geometry were checked against the source; only the explicit display-domain net reassignment was permitted. New ground-plane fill accommodates added pads.
- Six display tests include rejection of an always-enabled MISO return, direct host clock/rail bypass, wrong translator supply and a floating unused buffer input. Five system-power tests also pass.
- Source-hash-guarded checkpoint: `archive/handset-before-display-interface/9909b117f014/`.

## Next work

The subsequent routing update completes the interface copper and ground returns. Establish panel/CTP load and capacitor effective-value evidence, regulator thermal margin, off/on sequencing, reset timing, deselect/reselect MISO timing and external cable signal integrity. Confirm purchased FPC orientation and touch option. Backlight LED current/thermal qualification and expansion enable/fault control remain separate open work.

**DO NOT FABRICATE OR POWER.** This change resolves the direct shared-rail topology in CAD; it does not close electrical qualification or the release checklist.
