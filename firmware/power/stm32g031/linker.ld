ENTRY(Reset_Handler)
MEMORY {
 FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 60K
 RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 8K
}
/* Last two 2 KiB flash pages are reserved for a future durable journal. */
_stack_top = ORIGIN(RAM) + LENGTH(RAM);
_stack_limit = _stack_top - 1024;
SECTIONS {
 .vectors : ALIGN(256) { KEEP(*(.vectors)) } > FLASH
 .text : { *(.text*) *(.rodata*) } > FLASH
 .ARM.exidx : { *(.ARM.exidx*) } > FLASH
 .data : { . = ALIGN(4); _sdata = .; *(.data*) . = ALIGN(4); _edata = .; } > RAM AT>FLASH
 _sidata = LOADADDR(.data);
 .bss (NOLOAD) : { . = ALIGN(4); _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .; } > RAM
 /DISCARD/ : { *(.comment*) *(.note*) }
 ASSERT(_ebss <= _stack_limit, "RAM exceeds reserved stack limit")
}
