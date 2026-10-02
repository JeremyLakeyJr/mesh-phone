// Inhibited commissioning image. No flash writes or charge-arming implementation.
#include "stm32g031xx.h"
#include "../charger.hpp"

static volatile uint32_t ticks;
struct Diagnostics {
    uint32_t signature, reset_cause, option_bytes, loops, bus_errors;
    uint32_t initialized, state;
};
extern "C" {
volatile Diagnostics supervisor_diagnostics;
void SysTick_Handler() { ++ticks; }
[[noreturn]] void Default_Handler() {
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN;
    (void)RCC->IOPENR;
    GPIOA->BSRR = 1u << 16;
    GPIOA->MODER = (GPIOA->MODER & ~3u) | 1u;
    __disable_irq();
    for (;;) {} // No watchdog refresh: reset returns PA0 to high impedance.
}
}
void operator delete(void*) noexcept { Default_Handler(); }
void operator delete(void*, unsigned int) noexcept { Default_Handler(); }
extern "C" void __cxa_pure_virtual() { Default_Handler(); }

static void af(GPIO_TypeDef* port, unsigned pin, unsigned function) {
    port->BSRR = 1u << pin; // Release before selecting open-drain AF.
    port->OTYPER |= 1u << pin;
    port->PUPDR &= ~(3u << (2*pin)); // External pull-ups, or TCA9800 B current sources.
    port->AFR[pin/8] = (port->AFR[pin/8] & ~(15u << (4*(pin%8)))) | (function << (4*(pin%8)));
    port->MODER = (port->MODER & ~(3u << (2*pin))) | (2u << (2*pin));
}
static bool bounded(volatile uint32_t& reg, uint32_t mask, uint32_t expected) {
    for (uint32_t n=0;n<160000;++n) if ((reg&mask)==expected) return true;
    return false;
}
static void setup() {
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;
    (void)RCC->IOPENR;
    GPIOA->BSRR = 1u << 16; // First action: PA0 low before output mode.
    GPIOA->OTYPER &= ~1u;
    GPIOA->PUPDR &= ~3u;
    GPIOA->MODER = (GPIOA->MODER & ~3u) | 1u;
    supervisor_diagnostics.signature=0x47503130; // GP10 commissioning format
    supervisor_diagnostics.reset_cause=RCC->CSR;
    supervisor_diagnostics.option_bytes=FLASH->OPTR; // Observe, never rewrite option bytes.
    RCC->CR |= RCC_CR_HSION;
    if (!bounded(RCC->CR,RCC_CR_HSIRDY,RCC_CR_HSIRDY)) Default_Handler();
    RCC->CFGR &= ~(RCC_CFGR_SW | RCC_CFGR_HPRE | RCC_CFGR_PPRE);
    if (!bounded(RCC->CFGR,RCC_CFGR_SWS,RCC_CFGR_SWS_HSISYS)) Default_Handler();
    RCC->CR &= ~RCC_CR_HSIDIV; // HSI16 / 1; HCLK and PCLK 16 MHz.
    if (SysTick_Config(16000)) Default_Handler();
    IWDG->KR=0xcccc; IWDG->KR=0x5555;
    IWDG->PR=3; IWDG->RLR=999; // /32, 1000 counts: nominal ~1 s, LSI tolerance applies.
    if (!bounded(IWDG->SR,7,0)) Default_Handler();
    IWDG->KR=0xaaaa;
    RCC->APBENR1 |= RCC_APBENR1_I2C1EN | RCC_APBENR1_I2C2EN;
    RCC->APBENR2 |= RCC_APBENR2_SYSCFGEN;
    (void)RCC->APBENR1;
    RCC->APBRSTR1 |= RCC_APBRSTR1_I2C1RST | RCC_APBRSTR1_I2C2RST;
    RCC->APBRSTR1 &= ~(RCC_APBRSTR1_I2C1RST | RCC_APBRSTR1_I2C2RST);
    RCC->CCIPR &= ~RCC_CCIPR_I2C1SEL; // PCLK, not a bootloader-selected clock.
    af(GPIOB,8,6); af(GPIOB,7,6);
    // 250 ns prescaler, 10 us low / 8 us high before synchronizer/filter delays.
    // Conservative Standard-mode bring-up timing; validate actual rise/fall times.
    I2C1->TIMINGR=0x30721f27;
    I2C1->CR1=I2C_CR1_PE;
    SYSCFG->CFGR1 |= SYSCFG_CFGR1_PA11_RMP | SYSCFG_CFGR1_PA12_RMP;
    af(GPIOA,11,6); af(GPIOA,12,6); // No internal pull-ups on the buffer B side.
    I2C2->OAR1=(0x42u<<1)|I2C_OAR1_OA1EN;
    I2C2->CR1=I2C_CR1_PE; // Polled, clock-stretching diagnostic slave only.
}

class Stm32PowerIO final : public handset::PowerIO {
    static constexpr uint32_t errors=I2C_ISR_NACKF|I2C_ISR_BERR|I2C_ISR_ARLO|I2C_ISR_OVR;
    bool wait(uint32_t wanted,uint32_t started) {
        for (uint32_t spins=0;spins<160000;++spins) {
            const uint32_t flags=I2C1->ISR;
            if (flags&errors) return false;
            if (flags&wanted) return true;
            if (uint32_t(ticks-started)>=25) return false;
        }
        return false; // Bounded even if SysTick is broken; IWDG is independent.
    }
    bool failed() {
        set_charge_arm(false);
        I2C1->CR1=0;
        I2C1->ICR=I2C_ICR_STOPCF|I2C_ICR_NACKCF|I2C_ICR_BERRCF|I2C_ICR_ARLOCF|I2C_ICR_OVRCF;
        I2C1->CR1=I2C_CR1_PE;
        ++supervisor_diagnostics.bus_errors;
        return false;
    }
    bool start(uint8_t address,uint32_t& now) {
        now=ticks;
        if (address!=0x41 && address!=0x6a) return false;
        if (I2C1->ISR&I2C_ISR_BUSY) return false; // No automatic stuck-bus recovery/rearming.
        I2C1->ICR=I2C_ICR_STOPCF|I2C_ICR_NACKCF|I2C_ICR_BERRCF|I2C_ICR_ARLOCF|I2C_ICR_OVRCF;
        return true;
    }
public:
    bool set_charge_arm(bool enabled) override {
        GPIOA->BSRR=1u<<16; // This build has no path that drives PA0 high.
        return !enabled && !(GPIOA->ODR&1u) && !(GPIOA->IDR&1u);
    }
    bool load_inhibit(bool& inhibited) override {
        inhibited=true;
        return false; // Persistent storage is not implemented: never fabricate a valid record.
    }
    bool save_inhibit(bool) override { return false; }
    bool write(uint8_t a,uint8_t r,uint8_t v) override {
        uint32_t now;
        if (!start(a,now)) return failed();
        I2C1->CR2=(uint32_t(a)<<1)|(2u<<16)|I2C_CR2_AUTOEND|I2C_CR2_START;
        if (!wait(I2C_ISR_TXIS,now)) return failed();
        I2C1->TXDR=r;
        if (!wait(I2C_ISR_TXIS,now)) return failed();
        I2C1->TXDR=v;
        if (!wait(I2C_ISR_STOPF,now)) return failed();
        I2C1->ICR=I2C_ICR_STOPCF;return true;
    }
    bool read(uint8_t a,uint8_t r,uint8_t& v) override {
        uint32_t now;
        if (!start(a,now)) return failed();
        I2C1->CR2=(uint32_t(a)<<1)|(1u<<16)|I2C_CR2_START;
        if (!wait(I2C_ISR_TXIS,now)) return failed();
        I2C1->TXDR=r;
        if (!wait(I2C_ISR_TC,now)) return failed();
        I2C1->CR2=(uint32_t(a)<<1)|(1u<<16)|I2C_CR2_RD_WRN|I2C_CR2_AUTOEND|I2C_CR2_START;
        if (!wait(I2C_ISR_RXNE,now)) return failed();
        const uint8_t result=uint8_t(I2C1->RXDR);
        if (!wait(I2C_ISR_STOPF,now)) return failed();
        I2C1->ICR=I2C_ICR_STOPCF;v=result;return true;
    }
};

static void diagnostic_host() {
    static uint8_t frame[8],index;
    const uint32_t flags=I2C2->ISR;
    if (flags&I2C_ISR_ADDR) {
        frame[0]=1; frame[1]=1; // Version 1, permanently charge-inhibited image.
        frame[2]=uint8_t(supervisor_diagnostics.state);
        frame[3]=uint8_t(supervisor_diagnostics.bus_errors);
        const uint32_t cause=supervisor_diagnostics.reset_cause;
        for (unsigned n=0;n<4;++n) frame[4+n]=uint8_t(cause>>(8*n));
        index=0;I2C2->ICR=I2C_ICR_ADDRCF;
    }
    if (flags&I2C_ISR_RXNE) (void)I2C2->RXDR; // Discard every write; no authorization command exists.
    if (flags&I2C_ISR_TXIS) I2C2->TXDR=index<8 ? frame[index++] : 0xff;
    I2C2->ICR=flags&(I2C_ICR_STOPCF|I2C_ICR_NACKCF|I2C_ICR_BERRCF|I2C_ICR_ARLOCF|I2C_ICR_OVRCF);
}
extern "C" int main() {
    setup();
    Stm32PowerIO io;
    handset::Charger charger(io);
    supervisor_diagnostics.initialized=charger.begin(ticks,false);
    supervisor_diagnostics.state=uint32_t(charger.state());
    for (;;) {
        io.set_charge_arm(false);
        diagnostic_host();
        ++supervisor_diagnostics.loops;
        IWDG->KR=0xaaaa; // Only the foreground loop refreshes; no IRQ/background refresh.
        __WFI();
    }
}
extern "C" {
extern uint32_t _sidata,_sdata,_edata,_sbss,_ebss;
void runtime_start() {
    uint32_t* src=&_sidata;
    for (uint32_t* d=&_sdata;d<&_edata;) *d++=*src++;
    for (uint32_t* d=&_sbss;d<&_ebss;) *d++=0;
    main();
    Default_Handler();
}
}
