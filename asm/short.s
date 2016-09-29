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

	MOV.W	#0x1d00, R1
	CLR	SR
	
	MOV.W	&0x0350, R8
	ADDC.W	R1, 0x1000(PC)
	PUSH.W	@R1+
	
	MOV.W	&0x0350, R9
	SUB.W	R8, R9
	MOV.W	R9 , &.data0

	
 	MOV.W	#0x1d00, R1
	CLR	SR
	
	MOV.W	&0x0350, R10
	ADDC.W	R0, 0x1000(PC)
	PUSH.W	@R2+
	
	MOV.W	&0x0350, R11
	SUB.W	R10, R11
	MOV.W	R11, &.data1

	
	MOV.W	#0x1d00, R1
	CLR	SR
	
	MOV.W	&0x0350, R12
	PUSH.W	@R1+
	
	MOV.W	&0x0350, R13
	SUB.W	R12, R13
	MOV.W	R13, &.data2

	
	MOV.W	#0x1d00, R1
	CLR	SR
	
	MOV.W	&0x0350, R14
	PUSH.W	@R2+
	
	MOV.W	&0x0350, R15
	SUB.W	R14, R15
	MOV.W	R15, &.data3

	
.halt:
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	.word	0x3fff	; halt
	JMP	.halt
