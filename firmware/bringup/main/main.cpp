#include <atomic>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cinttypes>
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/usb_serial_jtag.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "board.hpp"
#include "session.hpp"

namespace {
struct Record { char text[160]; };
QueueHandle_t records, commands;
TaskHandle_t scan_task;
std::atomic<unsigned> queue_drops{0}, usb_drops{0};
unsigned sequence = 0; // Scanner task is the only record producer.
void record(const char *format, ...) __attribute__((format(printf, 1, 2)));
void record(const char *format, ...) {
    Record r{};
    int prefix = std::snprintf(r.text, sizeof(r.text), "\nseq=%u t_ms=%" PRId64 " ",
                               ++sequence, esp_timer_get_time()/1000);
    va_list args; va_start(args, format);
    std::vsnprintf(r.text+prefix, sizeof(r.text)-prefix, format, args);
    va_end(args);
    if (xQueueSend(records, &r, 0) != pdTRUE) ++queue_drops;
}
class Bus final : public keypad::Bus {
    i2c_master_dev_handle_t device_ = nullptr;
public:
    esp_err_t setup() {
        i2c_master_bus_config_t config{};
        config.i2c_port = I2C_NUM_0;
        config.sda_io_num = static_cast<gpio_num_t>(board::sda_gpio);
        config.scl_io_num = static_cast<gpio_num_t>(board::scl_gpio);
        config.clk_source = I2C_CLK_SRC_DEFAULT;
        config.glitch_ignore_cnt = 7;
        config.flags.enable_internal_pullup = false; // PCB R3/R4.
        i2c_master_bus_handle_t bus = nullptr;
        auto err = i2c_new_master_bus(&config, &bus);
        if (err != ESP_OK) return err;
        i2c_device_config_t dev{};
        dev.dev_addr_length = I2C_ADDR_BIT_LEN_7;
        dev.device_address = keypad::Controller::address;
        dev.scl_speed_hz = board::i2c_hz;
        err = i2c_master_bus_add_device(bus, &dev, &device_);
        if (err != ESP_OK) i2c_del_master_bus(bus);
        return err;
    }
    bool read(std::uint8_t address, std::uint8_t reg, std::uint8_t &value) override {
        return device_ && address == keypad::Controller::address &&
            i2c_master_transmit_receive(device_, &reg, 1, &value, 1, board::transfer_timeout_ms) == ESP_OK;
    }
    bool write(std::uint8_t address, std::uint8_t reg, std::uint8_t value) override {
        const std::uint8_t bytes[]{reg,value};
        return device_ && address == keypad::Controller::address &&
            i2c_master_transmit(device_, bytes, sizeof(bytes), board::transfer_timeout_ms) == ESP_OK;
    }
};
void irq(void *) {
    BaseType_t wake = pdFALSE;
    vTaskNotifyGiveFromISR(scan_task, &wake);
    if (wake) portYIELD_FROM_ISR();
}
void scanner(void *) {
    scan_task = xTaskGetCurrentTaskHandle();
    Bus bus;
    const esp_err_t bus_error = bus.setup();
    gpio_config_t config{};
    config.pin_bit_mask = 1ULL << board::irq_gpio;
    config.mode = GPIO_MODE_INPUT;
    config.intr_type = GPIO_INTR_DISABLE;
    esp_err_t irq_error = gpio_config(&config);
    if (irq_error == ESP_OK) irq_error = gpio_install_isr_service(0);
    if (irq_error == ESP_OK) irq_error = gpio_isr_handler_add(static_cast<gpio_num_t>(board::irq_gpio), irq, nullptr);
    if (irq_error == ESP_OK) irq_error = gpio_set_intr_type(static_cast<gpio_num_t>(board::irq_gpio), GPIO_INTR_NEGEDGE);
    gpio_intr_disable(static_cast<gpio_num_t>(board::irq_gpio));
    keypad::Controller controller(bus);
    bringup::Session<keypad::Controller> session(controller);
    record("BOOT keypad commissioning; SDA=10 SCL=9 IRQ=8 bus=%d irq=%d", bus_error, irq_error);
    record("Release all keys; commands: start, stop, status. No peripheral power enables.");
    std::int64_t last_status = 0;
    for (;;) {
        ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(board::poll_ms));
        bringup::Command command;
        if (xQueueReceive(commands, &command, 0) == pdTRUE) {
            if (command == bringup::Command::start) {
                if (session.active()) record("START rejected: already active");
                else if (bus_error != ESP_OK || irq_error != ESP_OK) record("START rejected: hardware setup failed; reset required");
                else if (session.start()) {
                    if (gpio_intr_enable(static_cast<gpio_num_t>(board::irq_gpio)) != ESP_OK) {
                        session.stop(); record("FAULT IRQ enable failed; key state invalid");
                    } else record("START ready");
                } else record("FAULT initialize=%u; release keys before explicit restart", unsigned(session.fault()));
            } else if (command == bringup::Command::stop) {
                gpio_intr_disable(static_cast<gpio_num_t>(board::irq_gpio));
                session.stop(); record("STOP key state invalid; U2 scanning may remain configured");
            } else if (command == bringup::Command::invalid) record("ERROR commands: start, stop, status");
            last_status = 0;
        }
        if (session.active()) {
            const auto batch = session.poll();
            if (!session.active()) {
                gpio_intr_disable(static_cast<gpio_num_t>(board::irq_gpio));
                record("FAULT status=%u key state invalid; release keys then start", unsigned(batch.status));
            } else {
                for (unsigned i=0; i<batch.count; ++i) {
                    const auto &e = batch.events[i];
                    record("KEY SW%u row=%u col=%u %s", unsigned(e.row*4+e.column+1), unsigned(e.row), unsigned(e.column), e.pressed?"PRESS":"RELEASE");
                }
            }
        }
        const auto now = esp_timer_get_time();
        if (last_status == 0 || now-last_status >= 1000000) {
            record("STATUS active=%u valid=%u held=0x%04x fault=%u irq=%d queue_drop=%u usb_drop=%u",
                   unsigned(session.active()), unsigned(session.valid()), unsigned(session.held()), unsigned(session.fault()),
                   gpio_get_level(static_cast<gpio_num_t>(board::irq_gpio)), queue_drops.load(), usb_drops.load());
            last_status = now;
        }
        // Level-low IRQ gets another bounded batch; yield even under IRQ storms.
        if (session.active() && gpio_get_level(static_cast<gpio_num_t>(board::irq_gpio)) == 0)
            xTaskNotifyGive(scan_task);
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}
void usb(void *) {
    bringup::LineParser parser;
    for (;;) {
        char input[64];
        int count = usb_serial_jtag_read_bytes(input, sizeof(input), pdMS_TO_TICKS(10));
        for (int i=0; i<count; ++i) {
            bringup::Command command;
            if (parser.feed(input[i], command) && xQueueSend(commands, &command, 0) != pdTRUE) ++usb_drops;
        }
        Record r;
        // USB backpressure never blocks the I2C task. Sequence numbers and drop
        // counters expose lost/truncated records; each record starts a new line.
        for (unsigned i=0; i<8 && xQueueReceive(records, &r, 0)==pdTRUE; ++i) {
            const auto length = std::strlen(r.text);
            if (usb_serial_jtag_write_bytes(r.text, length, 0) != static_cast<int>(length)) ++usb_drops;
        }
    }
}
}
extern "C" void app_main() {
    records = xQueueCreate(64, sizeof(Record));
    commands = xQueueCreate(8, sizeof(bringup::Command));
    if (!records || !commands) return;
    usb_serial_jtag_driver_config_t config{};
    config.rx_buffer_size = 1024; config.tx_buffer_size = 2048;
    if (usb_serial_jtag_driver_install(&config) != ESP_OK) return;
    if (xTaskCreate(usb,"keypad_usb",4096,nullptr,3,nullptr) != pdPASS) return;
    if (xTaskCreate(scanner,"keypad_scan",6144,nullptr,5,nullptr) != pdPASS) {
        const char message[]="\nFATAL scanner task allocation failed\n";
        usb_serial_jtag_write_bytes(message,sizeof(message)-1,0);
    }
}
