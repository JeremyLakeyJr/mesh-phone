#pragma once
namespace board {
// GPIO numbers, not module pad numbers. Verified against core.kicad_sch.
inline constexpr int sda_gpio = 10; // U1.18
inline constexpr int scl_gpio = 9;  // U1.17
inline constexpr int irq_gpio = 8;  // U1.12
inline constexpr unsigned i2c_hz = 100000;
inline constexpr int transfer_timeout_ms = 20;
inline constexpr int poll_ms = 10;
}
