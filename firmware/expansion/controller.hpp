#pragma once
#include <cstdint>

namespace expansion {
// HAL must serialize the shared bus and bound each operation in time.
struct Bus {
    virtual ~Bus() = default;
    virtual bool write(std::uint8_t address, std::uint8_t reg, std::uint8_t value) = 0;
    virtual bool read(std::uint8_t address, std::uint8_t reg, std::uint8_t &value) = 0;
};
enum class State { unknown_reset_required, off, settling, enabled, fault_latched };
struct Qualification {
    bool load_and_startup_qualified = false;
    bool bus_timing_and_addresses_qualified = false;
    // Measured startup requirement, including margin; never inferred from ILIM.
    std::uint32_t settling_ms = 0;
};
class Controller {
public:
    static constexpr std::uint8_t address = 0x49;
    static constexpr std::uint32_t poll_deadline_ms = 100;
    explicit Controller(Bus &bus) : bus_(bus) {}
    State state() const { return state_; }

    // Explicit start/recovery request. No automatic retries after faults.
    bool initialize() {
        state_ = State::unknown_reset_required;
        // Verify latch BEFORE turning reset-default input pins into outputs.
        if (!write_checked(1, 0xF0) || !write_checked(2, 0x00) ||
            !write_checked(3, 0xFA) || !pins_match(0)) return fail();
        state_ = State::off;
        return true;
    }
    bool enable(const Qualification &q, std::uint32_t now) {
        if (state_ != State::off || !q.load_and_startup_qualified ||
            !q.bus_timing_and_addresses_qualified || !q.settling_ms ||
            q.settling_ms > 60000) return false;
        if (!configuration_matches(0xF0) || !write_checked(1, 0xF1) ||
            !pins_match(1)) return fail();
        settle_ms_ = q.settling_ms;
        started_ = last_poll_ = now;
        state_ = State::settling;
        return true;
    }
    bool disable() {
        const bool latched = state_ == State::fault_latched;
        if (state_ == State::unknown_reset_required) return false;
        if (!write_checked(1, 0xF0) || !configuration_matches(0xF0) ||
            !pins_match(0)) return fail();
        state_ = latched ? State::fault_latched : State::off;
        return true;
    }
    bool poll(std::uint32_t now) {
        if (state_ != State::settling && state_ != State::enabled) return false;
        if (static_cast<std::uint32_t>(now - last_poll_) > poll_deadline_ms)
            return latch_fault();
        last_poll_ = now;
        const std::uint8_t output = state_ == State::enabled ? 0xF5 : 0xF1;
        std::uint8_t inputs = 0;
        if (!configuration_matches(output) || !bus_.read(address, 0, inputs))
            return fail();
        if ((inputs & 5) != (output & 5)) return fail();
        if (!(inputs & 2)) return latch_fault();
        if (state_ == State::settling &&
            static_cast<std::uint32_t>(now - started_) >= settle_ms_) {
            if (!write_checked(1, 0xF5) || !pins_match(5)) return fail();
            state_ = State::enabled;
        }
        return true;
    }
private:
    Bus &bus_;
    State state_ = State::unknown_reset_required;
    std::uint32_t started_ = 0, last_poll_ = 0, settle_ms_ = 0;
    bool equals(std::uint8_t reg, std::uint8_t expected) {
        std::uint8_t value = 0;
        return bus_.read(address, reg, value) && value == expected;
    }
    bool write_checked(std::uint8_t reg, std::uint8_t value) {
        return bus_.write(address, reg, value) && equals(reg, value);
    }
    bool configuration_matches(std::uint8_t output) {
        return equals(1, output) && equals(2, 0) && equals(3, 0xFA);
    }
    bool pins_match(std::uint8_t outputs) {
        std::uint8_t inputs = 0;
        return bus_.read(address, 0, inputs) && (inputs & 5) == outputs;
    }
    bool fail() {
        // Best effort only. A failed transfer may have reached the peripheral.
        bus_.write(address, 1, 0xF0);
        state_ = State::unknown_reset_required;
        return false;
    }
    bool latch_fault() {
        if (!write_checked(1, 0xF0) || !configuration_matches(0xF0) ||
            !pins_match(0)) return fail();
        state_ = State::fault_latched;
        return false;
    }
};
} // namespace expansion
