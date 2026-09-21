# OWASSO-1 GPIO Allocation (conflict-resolved rev A)
| Function | GPIO | Notes / Conflict Resolution |
|---|---|---|
| I2C (SDA) | IO1 | Shared: PCF/MCP, PN532, MAX17048, cam SCCB |
| I2C (SCL) | IO2 | Same bus |
| LCD SPI (FSPI) | IO33-36 + IO26 BL | Dedicated bus; no SD conflict |
| SDMMC 4-bit | IO45-48 + IO41-42 CMD/CLK | Separate from RF SPI |
| Shared RF SPI (CC1101 + SX1262) | IO5-7 (SCK/MOSI/MISO) + CS pins IO3/28 | Same bus, separate CS |
| Camera DVP | IO9-18, IO21, IO30-32 | Contiguous; does not overlap LCD |
| IR (TX/RX) | IO24-25 | Separate from LCD SPI |
| LTE UART1 | IO43/44 + PWRKEY IO37 | Remapped via GPIO matrix |
| Modem VBAT note | VBAT to modem via SW_PWR; add 2A path (was insufficient) |
| Fuel-gauge header | J? 1x04 (VCC GND SDA SCL) | Added ME6211 footprint SOT-23-5 |
| ESP32-S3 footprint | WROOM-1-N16R8 (18x25.5mm 38-pin) | Fixed symbol footprint property |
