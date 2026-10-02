#pragma once
#include <stdint.h>

namespace handset {
// Integration must serialize ALL charger/expander access through this owner.
// No other task may read the read-to-clear fault registers.
struct PowerIO {
    virtual ~PowerIO() = default;
    virtual bool read(uint8_t address, uint8_t reg, uint8_t& value) = 0;
    virtual bool write(uint8_t address, uint8_t reg, uint8_t value) = 0;
    // Durable, atomic storage; missing/corrupt records MUST return false.
    virtual bool load_inhibit(bool& inhibited) = 0;
    virtual bool save_inhibit(bool inhibited) = 0;
    // Dedicated PA0/Q8 permission, independent of the charger I2C bus.
    // HAL must preload low before selecting push-pull output. Missing HAL fails closed.
    virtual bool set_charge_arm(bool) { return false; }
};
enum class Source { none, legacy500, typeC };
enum class State { inhibited, idle, waiting, charging, fault };
class Charger {
    PowerIO& io;
    bool qualified = false, allowed = false, started = false, ce = false;
    Source active = Source::none;
    uint32_t last = 0;
    State current = State::inhibited;
    static constexpr uint8_t charger = 0x6a, gpio = 0x41;
    static constexpr uint8_t registers[6] = {3,5,6,7,10,11};
    static constexpr uint8_t values[6] = {0x43,0x25,0x56,0x99,0x40,0xe0};
    bool checked(uint8_t a, uint8_t r, uint8_t v) {
        uint8_t actual = 0;
        return io.write(a,r,v) && io.read(a,r,actual) && actual == v;
    }
    bool stop() {
        // Remove the independent permission BEFORE any potentially failing I2C call.
        bool arm_off = io.set_charge_arm(false);
        // Attempt all shutdown operations even after a bus failure.
        bool a = checked(gpio,1,0);
        bool b = checked(charger,4,0x85);
        bool c = checked(charger,8,0x49);
        active = Source::none; ce = false;
        return arm_off && a && b && c;
    }
    void trip() {
        allowed = false;
        current = State::fault;
        // Q8 can inhibit with a broken I2C bus. CPU hangs still require IWDG reset.
        stop();
        io.save_inhibit(true);
    }
    bool status(uint8_t& inputs, bool& ready) {
        uint8_t s0=0,s1=0,flags=0;
        if (!io.read(gpio,0,inputs) || !io.read(charger,0,s0) ||
            !io.read(charger,1,s1) || !io.read(charger,2,flags)) return false;
        // TS-open, OVP, safety timer, TS/OVP/OCP historical fault, eFuse /FAULT.
        // UVLO is not auto-cleared into a charge attempt: pack review required.
        if ((s0 & 0x80) || (s1 & 0xc4) || (flags & 0x87) || !(inputs & 8)) return false;
        ready = (s0 & 1) && (((s1 >> 3) & 3) != 1);
        return true;
    }
    bool configuration() {
        uint8_t v=0;
        for (unsigned i=0;i<6;++i)
            if (!io.read(charger,registers[i],v) || v != values[i]) return false;
        if (!io.read(gpio,3,v) || (v & 15) != 12) return false;
        if (!io.read(gpio,0x50,v) || v != 0x40) return false;
        const uint8_t out = (active==Source::legacy500 ? 2 : 0) | (ce ? 1 : 0);
        if (!io.read(gpio,1,v) || (v & 15) != out) return false;
        if (!io.read(charger,8,v) || v != (active==Source::typeC ? 0x4e : active==Source::legacy500 ? 0x4c : 0x49)) return false;
        return io.read(charger,4,v) && v == (active==Source::typeC ? 0x4d : active==Source::legacy500 ? 0x39 : 0x85);
    }
public:
    explicit Charger(PowerIO& transport):io(transport) {}
    State state() const { return current; }
    bool begin(uint32_t now, bool exact_pack_qualified) {
        qualified = exact_pack_qualified;
        allowed = false; started = false; active = Source::none;
        bool inhibited = true;
        if (!io.set_charge_arm(false)) { trip(); return false; }
        if (!io.load_inhibit(inhibited)) { trip(); return false; }
        // Sticky session marker precedes all charging: unexpected reboot inhibits recovery.
        if (!io.save_inhibit(true) || !stop() || !checked(gpio,3,0x0c) ||
            !checked(gpio,0x50,0x40)) { trip(); return false; }
        uint8_t inputs=0; bool ready=false;
        if (!status(inputs,ready)) { trip(); return false; }
        for (unsigned i=0;i<6;++i)
            if (!checked(charger,registers[i],values[i])) { trip(); return false; }
        started = true; last = now;
        allowed = qualified && !inhibited;
        current = allowed ? State::idle : State::inhibited;
        return true;
    }
    // Call on source events immediately and periodically <=1000 ms.
    // legacy_granted must come from the USB stack, revoked on suspend/reset/detach.
    void poll(uint32_t now, bool legacy_granted) {
        if (!started || !allowed || current==State::fault) return;
        if (uint32_t(now-last)>1000) { trip(); return; }
        last = now;
        uint8_t inputs=0; bool ready=false;
        if (!status(inputs,ready) || !configuration()) { trip(); return; }
        Source wanted = !(inputs & 4) ? Source::typeC : legacy_granted ? Source::legacy500 : Source::none;
        if (wanted==Source::none) {
            if (active!=Source::none && !stop()) { trip(); return; }
            current = State::idle; return;
        }
        if (wanted != active) {
            if (!stop() || !checked(charger,8,wanted==Source::typeC ? 0x4e : 0x4c) ||
                !checked(charger,4,wanted==Source::typeC ? 0x4d : 0x39) ||
                !checked(gpio,1,wanted==Source::legacy500 ? 2 : 0)) { trip(); return; }
            active=wanted;
        }
        // Leave legacy IN authorized while waiting for power-good; CE stays off.
        if (!status(inputs,ready)) { trip(); return; }
        if ((wanted==Source::typeC && (inputs & 4)) ||
            (wanted==Source::legacy500 && !(inputs & 4))) {
            if (!stop()) { trip(); return; }
            current=State::waiting; return;
        }
        if (!ready) {
            if (!io.set_charge_arm(false)) { trip(); return; }
            if (ce && !checked(gpio,1,wanted==Source::legacy500 ? 2 : 0)) { trip(); return; }
            ce=false; current=State::waiting; return;
        }
        if (!ce) {
            // All policy/status checks and expander readback precede the final permission.
            if (!checked(gpio,1,wanted==Source::typeC ? 1 : 3) ||
                !io.set_charge_arm(true)) { trip(); return; }
        }
        ce=true;
        current=State::charging;
    }
    // Does not clear the sticky inhibit. Recovery requires explicit service review
    // with outputs disabled and a separately audited persistent-record reset.
    void shutdown() { allowed=false; if (!stop()) trip(); else current=State::inhibited; }
};
}
