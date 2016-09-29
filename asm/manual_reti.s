.section .resetvec, "aw"
.balign 2
	.word	_start

.section .rodata
.balign 2
.data0:	.byte	0
.data1:	.byte	0
.data2:	.byte	0
.data3:	.byte	0

.section .text
.balign 2
_start:
	;; disable watchdog timer
	MOV.W	#23168, &0x015C

	;; abort and halt
	jmp	.go
.abort:
	jmp	.abort
.go:

	;; timer init
	MOV.W	#16, &0x0342
	MOV.W	#512, &0x0340

	;; timer start
	MOV.W	#0, &0x0350
	MOV.W	#50000, &0x0352
	BIS.W	#16, &0x0340

;;; tests begin

	;; repeat twice
	mov	#0x1f00, r1
	push	#.test0_call1
	push	r3
	push	#.test0_call0
	push	r3

	mov	&0x0350, r14
	reti
.test0_call0:
	reti
.test0_call1:
	mov	&0x0350, r15
	sub	r14, r15
	mov.b	r15, &.data0

	mov	r3, r2
	mov	r3, r14
	mov	r3, r15

	;; repeat three times
	mov	#0x1f00, r1
	push	#.test1_call2
	push	r3
	push	#.test1_call1
	push	r3
	push	#.test1_call0
	push	r3

	mov	&0x0350, r14
	reti
.test1_call0:
	reti
.test1_call1:
	reti
.test1_call2:
	mov	&0x0350, r15
	sub	r14, r15
	mov.b	r15, &.data1

	mov	r3, r2
	mov	r3, r14
	mov	r3, r15

	;; repeat four times
	mov	#0x1f00, r1
	push	#.test2_call3
	push	r3
	push	#.test2_call2
	push	r3
	push	#.test2_call1
	push	r3
	push	#.test2_call0
	push	r3

	mov	&0x0350, r14
	reti
.test2_call0:
	reti
.test2_call1:
	reti
.test2_call2:
	reti
.test2_call3:
	mov	&0x0350, r15
	sub	r14, r15
	mov.b	r15, &.data2

	mov	r3, r2
	mov	r3, r14
	mov	r3, r15

	;; repeat five times
	mov	#0x1f00, r1
	push	#.test3_call4
	push	r3
	push	#.test3_call3
	push	r3
	push	#.test3_call2
	push	r3
	push	#.test3_call1
	push	r3
	push	#.test3_call0
	push	r3

	mov	&0x0350, r14
	reti
.test3_call0:
	reti
.test3_call1:
	reti
.test3_call2:
	reti
.test3_call3:
	reti
.test3_call4:
	mov	&0x0350, r15
	sub	r14, r15
	mov.b	r15, &.data3

	mov	r3, r2
	mov	r3, r14
	mov	r3, r15

;;; tests end

	;; landing pad
.halt:
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	JMP	.halt
