#include "../charger.hpp"
#include <array>
#include <cassert>
#include <iostream>
#include <tuple>
#include <vector>
using namespace handset;
struct Fake : PowerIO {
    std::array<std::array<uint8_t,256>,128> regs{};
    bool latch=false, store_ok=true, bus_ok=true;
    bool arm=false, arm_ok=true;
    std::vector<bool> arm_writes;
    std::vector<char> operations;
    int fail_write=-1, count=0;
    std::vector<std::tuple<int,int,int>> writes;
    Fake() { regs[0x41][0]=8; regs[0x6a][0]=1; }
    bool read(uint8_t a,uint8_t r,uint8_t& v) override {
        operations.push_back('r');
        if (!bus_ok) return false;
        v=regs[a][r]; if (a==0x6a && r==2) regs[a][r]=0;
        if (a==0x6a && r==1) regs[a][r]&=0xf8;
        return true;
    }
    bool write(uint8_t a,uint8_t r,uint8_t v) override {
        operations.push_back('w');
        writes.emplace_back(a,r,v); if (count++==fail_write) return false; if (!bus_ok) return false; regs[a][r]=v; return true;
    }
    bool load_inhibit(bool& v) override { v=latch; return store_ok; }
    bool save_inhibit(bool v) override { if (!store_ok) return false; latch=v; return true; }
    bool set_charge_arm(bool enabled) override {
        operations.push_back(enabled ? 'A' : 'D'); arm_writes.push_back(enabled);
        if (!arm_ok) return false;
        arm=enabled; return true;
    }
};
int main() {
    { Fake f; Charger c(f); assert(c.begin(0,true)); c.poll(1,false);
      assert(c.state()==State::charging && f.regs[0x41][1]==1 && f.latch && f.arm);
      auto n=f.writes.size(); c.poll(2,false); assert(f.writes.size()==n); // No CE/timer cycling.
      f.regs[0x41][0]=12; c.poll(3,false); assert(c.state()==State::idle && f.regs[0x41][1]==0);
      f.regs[0x41][0]=8; c.poll(4,false); assert(c.state()==State::charging);
      Charger reboot(f); assert(reboot.begin(5,true)); reboot.poll(6,false); assert(reboot.state()==State::inhibited);
    }
    { Fake f; f.regs[0x41][0]=12; f.regs[0x6a][0]=0; Charger c(f); assert(c.begin(0,true));
      c.poll(1,true); assert(c.state()==State::waiting && f.regs[0x41][1]==2);
      f.regs[0x6a][0]=1; c.poll(2,true); assert(c.state()==State::charging && f.regs[0x41][1]==3);
      c.poll(3,false); assert(c.state()==State::idle && f.regs[0x41][1]==0);
    }
    { Fake f; Charger c(f); assert(c.begin(0,false)); c.poll(1,false); assert(c.state()==State::inhibited); }
    for (int failure=0;failure<8;++failure) {
      Fake f; Charger c(f); assert(c.begin(0,true)); c.poll(1,false);
      switch(failure) {
      case 0:f.regs[0x6a][1]=4;break; // Safety timer, even after read-to-clear.
      case 1:f.regs[0x6a][0]=0x81;break; // NTC open.
      case 2:f.regs[0x41][0]=0;break; // eFuse fault.
      case 3:f.regs[0x6a][3]=0x46;break; // Register reset/drift.
      case 4:f.regs[0x6a][2]=1;break; // Battery OCP history.
      case 5:f.bus_ok=false;break;
      case 6:f.regs[0x41][3]=15;break; // Expander reset.
      case 7:break; // Missed deadline.
      }
      c.poll(failure==7 ? 1002 : 2,false); assert(c.state()==State::fault && f.latch && !f.arm);
      f.bus_ok=true; f.regs[0x6a][1]=0; c.poll(1003,false); assert(c.state()==State::fault);
    }
    { Fake f; f.store_ok=false; Charger c(f); assert(!c.begin(0,true)); assert(c.state()==State::fault); }
    { Fake f; Charger c(f); assert(c.begin(0xfffffff0u,true)); c.poll(5,false); assert(c.state()==State::charging); }
    // Fail every startup/enable write in turn: none may report charging.
    { Fake baseline; Charger c(baseline); assert(c.begin(0,true)); c.poll(1,false);
      for (int n=0;n<baseline.count;++n) {
        Fake f; f.fail_write=n; Charger broken(f); broken.begin(0,true); broken.poll(1,false);
        assert(broken.state()==State::fault && f.latch);
      }
    }
    { Fake f; Charger c(f); assert(c.begin(0,true)); c.poll(1,false);
      f.regs[0x6a][1]=8; c.poll(2,false); // Temperature suspension without a historical fault.
      assert(c.state()==State::waiting && f.regs[0x41][1]==0);
      f.regs[0x6a][1]=0; c.poll(3,false); assert(c.state()==State::charging);
      f.regs[0x6a][0]=0; c.poll(4,false); assert(c.state()==State::waiting);
      c.shutdown(); assert(f.regs[0x41][1]==0 && f.latch);
    }
    // A retained expander output must not defeat independent shutdown on I2C failure.
    { Fake f; Charger c(f); assert(c.begin(0,true)); c.poll(1,false);
      assert(f.arm && f.regs[0x41][1]==1);
      f.bus_ok=false; f.operations.clear(); c.shutdown();
      assert(c.state()==State::fault && !f.arm && f.regs[0x41][1]==1);
      assert(f.operations.front()=='D');
    }
    // Disarm must precede storage and bus initialization even with retained outputs.
    { Fake f; f.arm=true; f.regs[0x41][1]=3; f.store_ok=false;
      Charger c(f); assert(!c.begin(0,true));
      assert(!f.arm && f.operations.front()=='D');
    }
    // Never claim charge permission if the independent GPIO operation fails.
    { Fake f; Charger c(f); assert(c.begin(0,true)); f.arm_ok=false;
      c.poll(1,false); assert(c.state()==State::fault && !f.arm);
    }
    // Reset is modeled as a high-Z pin discharged by the hardware pull-down.
    // Software must not re-arm merely because the expander retained its output.
    { Fake f; Charger c(f); assert(c.begin(0,true)); c.poll(1,false);
      f.arm=false; assert(f.regs[0x41][1]==1);
      Charger reboot(f); assert(reboot.begin(2,true)); reboot.poll(3,false);
      assert(reboot.state()==State::inhibited && !f.arm);
    }
    { Fake f; Charger c(f); assert(c.begin(0,false)); c.poll(1,false);
      for (bool enabled:f.arm_writes) assert(!enabled);
    }
    { struct MissingArmHAL : Fake {
          bool set_charge_arm(bool enabled) override { return PowerIO::set_charge_arm(enabled); }
      } f;
      Charger c(f); assert(!c.begin(0,true)); c.poll(1,false);
      assert(c.state()==State::fault && !f.arm);
    }
    { Fake f; Charger c(f); assert(c.begin(0,true)); c.poll(1,false);
      assert(f.operations.back()=='A'); auto count=f.arm_writes.size();
      c.poll(2,false); assert(f.arm_writes.size()==count);
      f.regs[0x6a][1]=8; c.poll(3,false); assert(!f.arm);
      f.regs[0x6a][1]=0; c.poll(4,false); assert(f.arm);
    }
    std::cout << "Charger sequencing, independent arm, bus-failure shutdown, reset, permissions and fault tests passed\n";
}
