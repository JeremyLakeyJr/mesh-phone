#include "../controller.hpp"
#include <array>
#include <cassert>
#include <iostream>
#include <utility>
#include <vector>
using namespace expansion;
struct Fake : Bus {
    std::array<std::uint8_t, 4> r{2, 0xFF, 0, 0xFF};
    bool fault = false, stuck = false, ignore_write = false;
    unsigned calls = 0, fail_at = 0;
    std::vector<std::pair<unsigned, unsigned>> writes;
    bool works() { return !stuck && ++calls != fail_at; }
    bool write(std::uint8_t a, std::uint8_t reg, std::uint8_t v) override {
        assert(a == 0x49 && reg > 0 && reg < 4);
        writes.emplace_back(reg, v);
        if (!works()) return false;
        if (!ignore_write) r[reg] = v;
        return true;
    }
    bool read(std::uint8_t a, std::uint8_t reg, std::uint8_t &v) override {
        assert(a == 0x49 && reg < 4);
        if (!works()) return false;
        v = reg ? r[reg] : ((r[1] & ~r[3] & 5) | (fault ? 0 : 2));
        return true;
    }
};
const Qualification qualified{true, true, 25};
int main() {
    {
        Fake b; Controller c(b);
        assert(c.state() == State::unknown_reset_required);
        assert(!c.enable(qualified, 0));
        assert(c.initialize());
        assert((b.writes[0] == std::make_pair(1u, 0xF0u)));
        assert((b.writes[2] == std::make_pair(3u, 0xFAu)));
        assert(!c.enable({}, 0));
        assert(!c.enable({true, false, 25}, 0));
        assert(!c.enable({false, true, 25}, 0));
        assert(!c.enable({true, true, 0}, 0));
        assert(!c.enable({true, true, 60001}, 0));
        assert(c.enable(qualified, 0));
        assert(b.r[1] == 0xF1 && c.poll(24));
        assert(c.state() == State::settling);
        assert(c.poll(25) && b.r[1] == 0xF5);
        const auto n = b.writes.size();
        assert(c.poll(50) && b.writes.size() == n);
        b.fault = true;
        assert(!c.poll(75) && b.r[1] == 0xF0);
        assert(c.state() == State::fault_latched);
        b.fault = false;
        assert(c.disable() && !c.enable(qualified, 80));
        assert(c.initialize() && c.enable(qualified, 80));
        b.stuck = true;
        assert(!c.disable());
        assert(c.state() == State::unknown_reset_required);
        assert(b.r[1] == 0xF1); // Software cannot claim it switched the rail off.
    }
    {
        Fake b; Controller c(b); assert(c.initialize());
        assert(c.enable(qualified, 0xFFFFFFF0));
        assert(c.poll(10) && c.state() == State::enabled); // Wrap-safe elapsed time.
        assert(!c.poll(111) && c.state() == State::fault_latched);
    }
    {
        Fake b; Controller c(b); assert(c.initialize()); assert(c.enable(qualified, 0));
        b.r[3] = 0xFF; // Expander brownout/reset.
        assert(!c.poll(25) && c.state() == State::unknown_reset_required);
    }
    {
        Fake b; Controller c(b); b.ignore_write = true;
        assert(!c.initialize() && c.state() == State::unknown_reset_required);
    }
    {
        Fake b; Controller c(b); assert(c.initialize()); assert(c.enable(qualified, 0));
        b.fault = true;
        assert(!c.poll(25) && c.state() == State::fault_latched);
        assert(b.r[1] == 0xF0); // A startup fault never arms the signals.
    }
    // Fail each transaction in startup, enabling and arm transition.
    for (unsigned failure = 1; failure <= 30; ++failure) {
        Fake b; Controller c(b); b.fail_at = failure;
        bool ok = c.initialize();
        if (ok) ok = c.enable(qualified, 0);
        if (ok) ok = c.poll(25);
        if (failure <= b.calls && !ok)
            assert(c.state() == State::unknown_reset_required);
    }
    std::cout << "Expansion controller tests passed\n";
}
