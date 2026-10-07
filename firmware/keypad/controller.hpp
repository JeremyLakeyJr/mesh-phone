#pragma once
#include <array>
#include <cstdint>

namespace keypad {
// Operations must be serialized with other U2 users and have bounded timeouts.
struct Bus {
    virtual ~Bus() = default;
    virtual bool read(std::uint8_t address, std::uint8_t reg, std::uint8_t &value) = 0;
    virtual bool write(std::uint8_t address, std::uint8_t reg, std::uint8_t value) = 0;
};
struct Event { std::uint8_t row = 0, column = 0; bool pressed = false; };
enum class Status { ready, reset_required, overflow, invalid_event, bus_error };
struct Batch {
    Status status = Status::reset_required;
    std::array<Event, 10> events{};
    unsigned count = 0;
    // Non-ready results invalidate the caller's entire held-key state.
};
class Controller {
public:
    static constexpr std::uint8_t address = 0x34;
    explicit Controller(Bus &bus) : bus_(bus) {}
    Status status() const { return state_; }
    // Commission with all keys released. Does not reset the shared MCU_EN net,
    // change GPIO directions/latches or enable peripheral power/backlight.
    bool initialize() {
        state_ = Status::reset_required;
        if (!checked(0x01, 0) || !checked(0x1d, 0x0f) ||
            !checked(0x1e, 0x0f) || !checked(0x1f, 0) ||
            !masked(0x29, 0x0f) || !masked(0x2a, 0x0f) ||
            !masked(0x2c, 0x0f) || !masked(0x2d, 0x0f) ||
            !checked(0x20, 0) || !checked(0x21, 0) || !checked(0x22, 0) ||
            !bus_.write(address, 0x03, 0)) return fail(Status::bus_error);
        // Bounded flush; no auto-increment, always pop KEY_EVENT_A.
        std::uint8_t count = 0, discard = 0;
        if (!bus_.read(address, 0x03, count) || (count & 15) > 10)
            return fail(Status::bus_error);
        for (unsigned i = 0; i < (count & 15); ++i)
            if (!bus_.read(address, 0x04, discard)) return fail(Status::bus_error);
        if (!bus_.read(address, 0x03, count) || (count & 15) != 0)
            return fail(Status::reset_required);
        // TI overflow erratum: OVR_FLOW_M and OVR_FLOW_IEN must both be set.
        if (!bus_.write(address, 0x02, 0x1f) || !checked(0x01, config))
            return fail(Status::bus_error);
        state_ = Status::ready;
        return true;
    }
    Batch poll() {
        Batch result;
        result.status = state_;
        if (state_ != Status::ready) return result;
        if (!configuration_matches()) return fault(Status::reset_required);
        std::uint8_t flags = 0, count = 0;
        if (!bus_.read(address, 0x02, flags) || !bus_.read(address, 0x03, count))
            return fault(Status::bus_error);
        if (flags & 8) return fault(Status::overflow);
        if ((count & 0x70) || (count & 15) > 10 || (flags & 6))
            return fault(Status::reset_required);
        result.count = count & 15;
        for (unsigned i = 0; i < result.count; ++i) {
            std::uint8_t raw = 0;
            if (!bus_.read(address, 0x04, raw)) return fault(Status::bus_error);
            if (!decode(raw, result.events[i])) return fault(Status::invalid_event);
        }
        // Publish no partial batch after errors, reset or overflow during drain.
        if (!bus_.read(address, 0x02, flags)) return fault(Status::bus_error);
        if (flags & 8) return fault(Status::overflow);
        if (!configuration_matches()) return fault(Status::reset_required);
        // Clear only key/CAD bits. An overflow arriving now stays latched.
        // CAD is ignored as an action because of TI's false-CAD erratum.
        if (!bus_.write(address, 0x02, 0x11)) return fault(Status::bus_error);
        result.status = Status::ready;
        return result;
    }
    static bool decode(std::uint8_t raw, Event &event) {
        const unsigned code = raw & 0x7f;
        if (!code) return false;
        const unsigned row = (code - 1) / 10, column = (code - 1) % 10;
        if (row >= 4 || column >= 4) return false;
        event = {static_cast<std::uint8_t>(row), static_cast<std::uint8_t>(column), bool(raw & 0x80)};
        return true;
    }
private:
    static constexpr std::uint8_t config = 0x29;
    Bus &bus_;
    Status state_ = Status::reset_required;
    bool fail(Status status) { state_ = status; return false; }
    Batch fault(Status status) { state_ = status; Batch b; b.status = status; return b; }
    bool matches(std::uint8_t reg, std::uint8_t expected) {
        std::uint8_t actual = 0;
        return bus_.read(address, reg, actual) && actual == expected;
    }
    bool checked(std::uint8_t reg, std::uint8_t value) {
        return bus_.write(address, reg, value) && matches(reg, value);
    }
    bool masked(std::uint8_t reg, std::uint8_t clear) {
        std::uint8_t value = 0;
        return bus_.read(address, reg, value) && checked(reg, value & ~clear);
    }
    bool configuration_matches() {
        return matches(0x01, config) && matches(0x1d, 0x0f) &&
               matches(0x1e, 0x0f) && matches(0x1f, 0);
    }
};
} // namespace keypad
