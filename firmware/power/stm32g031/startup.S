.syntax unified
.cpu cortex-m0plus
.thumb
.section .vectors,"a",%progbits
.global vectors
vectors:
.word _stack_top
.word Reset_Handler
.word Default_Handler
.word Default_Handler
.rept 7
.word 0
.endr
.word Default_Handler
.word 0
.word 0
.word Default_Handler
.word SysTick_Handler
.rept 32
.word Default_Handler
.endr
.section .text.Reset_Handler,"ax",%progbits
.global Reset_Handler
.type Reset_Handler,%function
.thumb_func
Reset_Handler:
 bl runtime_start
 b .
