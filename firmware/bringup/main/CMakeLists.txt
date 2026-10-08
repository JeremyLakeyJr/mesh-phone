idf_component_register(SRCS "main.cpp" INCLUDE_DIRS "." "../.."
                       REQUIRES esp_driver_i2c esp_driver_gpio esp_driver_usb_serial_jtag esp_timer)
target_compile_features(${COMPONENT_LIB} PRIVATE cxx_std_17)
target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Werror)
