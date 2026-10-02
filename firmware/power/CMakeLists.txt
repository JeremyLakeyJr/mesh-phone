# Legacy direct ESP32 charger adapter; not the active interface for the STM32 supervisor PCB.
# ESP-IDF 5.4 component; add firmware/power to the application's EXTRA_COMPONENT_DIRS.
idf_component_register(SRCS "esp_idf/power_io.cpp"
                       INCLUDE_DIRS "." "esp_idf"
                       REQUIRES esp_driver_i2c nvs_flash)
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
