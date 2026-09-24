# MAX-M10S integration review

Reviewed 2026-09-21. The user-supplied root HTML contains a Claude artifact;
the actual guide is in `MAX-M10S GNSS Module — Integration Manual_files/a_94hE.html`.
It is a secondary reference, not the manufacturer's integration manual.

Authoritative references:

- [u-blox integration manual UBX-20053088 R05](https://content.u-blox.com/sites/default/files/MAX-M10S_IntegrationManual_UBX-20053088.pdf), sections 3.2.3.1, 4.1 and appendix B.
- [u-blox data sheet UBX-20035208 R08](https://content.u-blox.com/sites/default/files/MAX-M10S_DataSheet_UBX-20035208.pdf), pin assignments and electrical limits.

## Decisions for the saved handset schematic

U12 is MAX-M10S-00B-01. Its connectivity manifest currently assigns VCC and
V_IO to +3V3, with VIO_SEL open. TXD connects to GPS_HOST_RX and RXD to
GPS_HOST_TX; TIMEPULSE connects to GPS_PPS. Ground pins 1, 10 and 12 are
assigned GND. These assignments agree with the manufacturer pin definitions.

Keep RESET_N open: the internal pull-up provides normal operation. Do not
adopt the artifact's recommendation to connect it directly to 3.3 V.
Keep V_BCKP open for the current design without a separate backup supply,
as specified by the official integration manual. Loss of the main supply
therefore loses retained GNSS state; hardware backup is not implemented.

J22 is the passive-antenna connection to RF_IN. VCC_RF and LNA_EN remain
unused. Its feed needs controlled impedance and transmitter isolation;
the schematic connection alone does not establish RF performance. The
official reference design allows additional input filtering for cellular
coexistence. Filter selection and isolation testing remain outstanding.

The artifact's suggestion that V_IO can independently bridge arbitrary
logic levels is incomplete: its voltage must also respect VCC + 0.3 V.
No direct connection from the handset lithium battery to GNSS supplies
is permitted by the module's voltage limits.

## Validation limits

This review checked the saved connectivity manifest against the official
pin and supply guidance. It does not certify routed power integrity,
antenna performance, decoupling placement, or the rest of the PCB. No
component positions or PCB wiring were changed by this review. Continue
the pending layout clearance and enclosure work separately.
