#include "../controller.hpp"
#include <cassert>
#include <deque>
#include <iostream>
#include <utility>
#include <vector>
using namespace keypad;
struct Fake : Bus {
    std::array<std::uint8_t, 48> reg{};
    std::deque<std::uint8_t> fifo;
    std::vector<std::pair<unsigned,unsigned>> writes;
    int fail_after = -1, operations = 0;
    bool ignore_write = false, overflow_on_pop = false, arrive_on_ack = false;
    bool ok() { ++operations; if (fail_after == 0) return false; if (fail_after > 0) --fail_after; return true; }
    bool read(std::uint8_t a, std::uint8_t r, std::uint8_t &v) override {
        assert(a == 0x34); if (!ok()) return false;
        v = reg.at(r);
        if (r == 3) v = static_cast<std::uint8_t>(fifo.size());
        if (r == 4) {
            v = fifo.empty() ? 0 : fifo.front();
            if (!fifo.empty()) fifo.pop_front();
            if (overflow_on_pop) reg[2] |= 8;
        }
        return true;
    }
    bool write(std::uint8_t a, std::uint8_t r, std::uint8_t v) override {
        assert(a == 0x34); if (!ok()) return false; writes.emplace_back(r,v);
        if (ignore_write) return true;
        if (r == 2) {
            if (arrive_on_ack) { fifo.push_back(0x81); reg[2] |= 9; arrive_on_ack = false; }
            reg[r] &= ~v;
            if (!fifo.empty()) reg[r] |= 1;
        } else if (r != 3) reg[r] = v;
        return true;
    }
};
int main() {
    unsigned tests = 0;
    { Fake b; Controller c(b); assert(c.poll().status == Status::reset_required);
      for(unsigned r : {0x29,0x2a,0x2c,0x2d}) b.reg[r]=0xff;
      b.reg[0x17]=0xa5; b.reg[0x23]=0x50;
      b.fifo = {0x81, 1}; assert(c.initialize());
      for(unsigned r : {0x29,0x2a,0x2c,0x2d}) { assert(b.reg[r]==0xf0); }
      assert(b.reg[0x17]==0xa5 && b.reg[0x23]==0x50); assert(b.fifo.empty());
      assert(b.reg[1] == 0x29); assert(b.reg[0x1d] == 15 && b.reg[0x1e] == 15);
      for (auto w : b.writes) assert(w.first < 0x17 || w.first > 0x19);
      for (auto w : b.writes) { assert(w.first < 0x23 || w.first > 0x25); }
      ++tests; }
    { Event e; for (unsigned r=0;r<4;++r) { for(unsigned col=0;col<4;++col) {
      for (unsigned press=0;press<2;++press) {
        assert(Controller::decode(static_cast<std::uint8_t>(r*10+col+1+(press?128:0)),e));
        assert(e.row==r && e.column==col && e.pressed==bool(press)); } } }
      for(unsigned code : {0,5,10,35,41,80,97,127}) { assert(!Controller::decode(static_cast<std::uint8_t>(code),e)); }
      ++tests; }
    { Fake b; Controller c(b); assert(c.initialize()); b.fifo={0x81,0x8c,1,12}; b.reg[2]=0x11;
      auto batch=c.poll(); assert(batch.status==Status::ready && batch.count==4);
      assert(batch.events[1].row==1 && batch.events[1].column==1 && batch.events[1].pressed);
      assert(!batch.events[3].pressed && b.fifo.empty()); assert(c.poll().count==0); ++tests; }
    { Fake b; Controller c(b); assert(c.initialize()); b.reg[2]=8;
      assert(c.poll().status==Status::overflow); b.reg[2]=0; assert(c.poll().status==Status::overflow); ++tests; }
    { Fake b; Controller c(b); assert(c.initialize()); b.fifo={0x81,0x82}; b.overflow_on_pop=true;
      auto batch=c.poll(); assert(batch.status==Status::overflow && batch.count==0); ++tests; }
    { Fake b; Controller c(b); assert(c.initialize()); b.fifo={0x81,0x85};
      auto batch=c.poll(); assert(batch.status==Status::invalid_event && batch.count==0); ++tests; }
    { Fake b; Controller c(b); assert(c.initialize()); b.reg[0x1e]=0;
      assert(c.poll().status==Status::reset_required); ++tests; }
    { Fake b; Controller c(b); assert(c.initialize()); b.arrive_on_ack=true;
      assert(c.poll().status==Status::ready); assert(b.reg[2]&8);
      assert(c.poll().status==Status::overflow); ++tests; }
    { Fake b; b.ignore_write=true; Controller c(b); assert(!c.initialize()); ++tests; }
    { Fake baseline; Controller good(baseline); assert(good.initialize());
      // Fail each read/write position in initialization and steady polling.
      for(int n=0;n<baseline.operations;++n) { Fake b; Controller c(b); b.fail_after=n;
        assert(!c.initialize()); assert(c.status()!=Status::ready); }
      for(int n=0;n<14;++n) { Fake b; Controller c(b); assert(c.initialize());
        b.fifo={0x81,1}; b.fail_after=n; auto batch=c.poll();
        assert(batch.status!=Status::ready && batch.count==0); }
      ++tests; }
    { Fake b; Controller c(b); assert(c.initialize());
      b.fifo={0x81,1,0x82,2,0x83,3,0x84,4,0x8b,11};
      auto batch=c.poll(); assert(batch.status==Status::ready && batch.count==10 && b.fifo.empty()); ++tests; }
    { Fake b; Controller c(b); assert(c.initialize()); b.fifo=std::deque<std::uint8_t>(11,0x81);
      auto batch=c.poll(); assert(batch.status==Status::reset_required && batch.count==0); ++tests; }
    std::cout << tests << " keypad firmware scenarios passed\n";
}
