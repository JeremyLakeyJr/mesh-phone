#include "power_io.hpp"

namespace handset {
i2c_master_dev_handle_t EspPowerIO::device(uint8_t address) const {
    return address==0x6a ? chg : address==0x41 ? exp : nullptr;
}
EspPowerIO::~EspPowerIO() {
    if (exp) i2c_master_bus_rm_device(exp);
    if (chg) i2c_master_bus_rm_device(chg);
    if (opened) nvs_close(storage);
}
esp_err_t EspPowerIO::init(i2c_master_bus_handle_t bus) {
    if (!bus || chg || exp || opened) return ESP_ERR_INVALID_STATE;
    esp_err_t err=nvs_open("powerctl",NVS_READWRITE,&storage);
    if (err!=ESP_OK) return err;
    opened=true;
    i2c_device_config_t config{};
    config.dev_addr_length=I2C_ADDR_BIT_LEN_7;
    config.device_address=0x6a;
    config.scl_speed_hz=100000;
    err=i2c_master_bus_add_device(bus,&config,&chg);
    if (err==ESP_OK) {
        config.device_address=0x41;
        err=i2c_master_bus_add_device(bus,&config,&exp);
    }
    if (err!=ESP_OK) {
        if (chg) i2c_master_bus_rm_device(chg);
        chg=nullptr; exp=nullptr;
        nvs_close(storage); opened=false;
    }
    return err;
}
bool EspPowerIO::read(uint8_t address,uint8_t reg,uint8_t& value) {
    auto dev=device(address);
    if (!dev || !opened) return false;
    uint8_t received=0;
    // Combined transaction preserves repeated START. No infinite transfer timeout.
    if (i2c_master_transmit_receive(dev,&reg,1,&received,1,25)!=ESP_OK) return false;
    value=received;
    return true;
}
bool EspPowerIO::write(uint8_t address,uint8_t reg,uint8_t value) {
    auto dev=device(address);
    if (!dev || !opened) return false;
    // Do not expose ship/reset or unrelated-device writes through this adapter.
    bool permitted=address==0x6a ? ((reg>=3 && reg<=8) || reg==10 || reg==11)
                                : (reg==1 || reg==3 || reg==0x50);
    if (!permitted) return false;
    const uint8_t data[]={reg,value};
    return i2c_master_transmit(dev,data,sizeof(data),25)==ESP_OK;
}
bool EspPowerIO::load_inhibit(bool& inhibited) {
    inhibited=true;
    if (!opened) return false;
    uint32_t record=0;
    if (nvs_get_u32(storage,"charge_guard",&record)!=ESP_OK) return false;
    if (record!=inhibited_record && record!=armed_record) return false;
    inhibited=record==inhibited_record;
    return true;
}
bool EspPowerIO::save_inhibit(bool inhibited) {
    if (!opened || !inhibited) return false;
    // Never return success merely because a value is visible in the NVS cache.
    if (nvs_set_u32(storage,"charge_guard",inhibited_record)!=ESP_OK ||
        nvs_commit(storage)!=ESP_OK) return false;
    uint32_t actual=0;
    return nvs_get_u32(storage,"charge_guard",&actual)==ESP_OK && actual==inhibited_record;
}
}
