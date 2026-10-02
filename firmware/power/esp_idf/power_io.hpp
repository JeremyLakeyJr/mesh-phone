#pragma once
#include "../charger.hpp"
#include "driver/i2c_master.h"
#include "nvs.h"

namespace handset {
// Single charging-task owner. The application owns and serializes the bus.
// Device callbacks/asynchronous transfers must not be configured for these handles.
class EspPowerIO final : public PowerIO {
    i2c_master_dev_handle_t chg=nullptr, exp=nullptr;
    nvs_handle_t storage=0;
    bool opened=false;
    static constexpr uint32_t inhibited_record=0x435047a5;
    static constexpr uint32_t armed_record=0x4350475a;
    i2c_master_dev_handle_t device(uint8_t address) const;
public:
    EspPowerIO() = default;
    ~EspPowerIO();
    EspPowerIO(const EspPowerIO&)=delete;
    EspPowerIO& operator=(const EspPowerIO&)=delete;
    // Call after successful nvs_flash_init(); never erase NVS on initialization failure.
    esp_err_t init(i2c_master_bus_handle_t bus);
    bool read(uint8_t address,uint8_t reg,uint8_t& value) override;
    bool write(uint8_t address,uint8_t reg,uint8_t value) override;
    bool load_inhibit(bool& inhibited) override;
    // Runtime can only inhibit. Arming belongs to a separately audited service procedure.
    bool save_inhibit(bool inhibited) override;
};
}
