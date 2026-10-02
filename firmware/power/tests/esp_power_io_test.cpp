#include "../esp_idf/power_io.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
static int adds=0,removed=0,closed=0,commits=0,write_calls=0;
static bool missing=true,commit_error=false,io_error=false,open_error=false,add_error=false;
static uint32_t persisted=0,pending=0;
static uint8_t last_reg=0,last_value=0;
esp_err_t nvs_open(const char* ns,int mode,nvs_handle_t* h) { assert(!strcmp(ns,"powerctl") && mode==NVS_READWRITE); *h=1; return open_error?-2:ESP_OK; }
void nvs_close(nvs_handle_t) { ++closed; }
esp_err_t nvs_get_u32(nvs_handle_t,const char* key,uint32_t* v) { assert(!strcmp(key,"charge_guard")); *v=persisted;return missing?-2:ESP_OK; }
esp_err_t nvs_set_u32(nvs_handle_t,const char*,uint32_t v) { pending=v;return ESP_OK; }
esp_err_t nvs_commit(nvs_handle_t) { ++commits; if(commit_error)return -2;persisted=pending;missing=false;return ESP_OK; }
esp_err_t i2c_master_bus_add_device(i2c_master_bus_handle_t,const i2c_device_config_t* c,i2c_master_dev_handle_t* h) {
    ++adds; assert(c->scl_speed_hz==100000 && (c->device_address==0x41 || c->device_address==0x6a));
    if(add_error && c->device_address==0x41)return -2;
    *h=reinterpret_cast<void*>(static_cast<uintptr_t>(c->device_address));return ESP_OK;
}
esp_err_t i2c_master_bus_rm_device(i2c_master_dev_handle_t) { ++removed;return ESP_OK; }
esp_err_t i2c_master_transmit_receive(i2c_master_dev_handle_t,const uint8_t* tx,size_t nt,uint8_t* rx,size_t nr,int timeout) {
    assert(nt==1 && nr==1 && timeout==25);last_reg=*tx;*rx=0x99;return io_error?-2:ESP_OK;
}
esp_err_t i2c_master_transmit(i2c_master_dev_handle_t,const uint8_t* tx,size_t n,int timeout) {
    assert(n==2 && timeout==25);++write_calls;last_reg=tx[0];last_value=tx[1];return io_error?-2:ESP_OK;
}
int main() {
    auto bus=reinterpret_cast<void*>(1);
    { handset::EspPowerIO io; bool inhibited=false;uint8_t v=0;
      assert(!io.read(0x6a,0,v));assert(io.init(bus)==ESP_OK);assert(io.init(bus)!=ESP_OK);
      assert(!io.load_inhibit(inhibited) && inhibited); // Missing record fails closed.
      persisted=0x4350475a;missing=false;assert(io.load_inhibit(inhibited) && !inhibited);
      commit_error=true;assert(!io.save_inhibit(true)); // No false success on failed commit.
      commit_error=false;assert(io.save_inhibit(true));assert(io.load_inhibit(inhibited) && inhibited);
      assert(!io.save_inhibit(false)); // Runtime cannot arm itself.
      persisted=123;assert(!io.load_inhibit(inhibited) && inhibited);
      assert(io.read(0x6a,7,v) && v==0x99 && last_reg==7);
      io_error=true;v=42;assert(!io.read(0x6a,7,v) && v==42);io_error=false;
      assert(!io.read(0x42,0,v));assert(!io.write(0x6a,9,0));
      assert(io.write(0x41,1,0) && last_reg==1 && last_value==0);
      assert(commits==2 && write_calls==1);
    }
    assert(removed==2 && closed==1);
    { handset::EspPowerIO io;add_error=true;assert(io.init(bus)!=ESP_OK); }
    assert(removed==3 && closed==2);add_error=false;
    { handset::EspPowerIO io;open_error=true;assert(io.init(bus)!=ESP_OK); }
    assert(removed==3 && closed==2);
    std::cout<<"ESP-IDF adapter host tests: transaction framing, timeouts, storage errors, inhibition and cleanup passed\n";
}
