.section .resetvec, "aw"
.balign 2
	.word	_start

.section .rodata
.balign 2
.data0:	.word	0
.data1:	.word	0
.data2:	.word	0
.data3:	.word	0
.data4:	.word	0
.data5:	.word	0
.data6:	.word	0
.data7:	.word	0
	
.section .text
.balign 2
_start:	
	;; disable watchdog timer
	MOV.W	#23168, &0x015C

	;; timer init
	MOV.W	#16, &0x0342
	MOV.W	#512, &0x0340

	;; timer start
	MOV.W	#0, &0x0350
	MOV.W	#-15536, &0x0352
	BIS.W	#16, &0x0340

	;; test code here!

	CLR	R2
	MOV	#0x1d10, R1
	MOV	#0xffff, R4
	
	MOV.W	&0x0350, R14
	PUSH	#0x1d00
	SUBC	R4, R0
	
	MOV.W	&0x0350, R15
	SUB.W	R14, R15
	MOV.W	R15, &.data0

	CLR	R2
	CLR	R14
	CLR	R15
	

	
.halt:
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	JMP	.halt
