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

	clr     r2              ;          
	clr     r14             ;
	clr     r15             ;
	
	mov     #7440,  r1      ;#0x1d10
	mov     #.exit1, &0x1d0e;!!!
	mov     #.call0, &0x1d10
	
	                                   
	mov     &0x0350,r14     ;0x0350    

	;and     @r0,    r0     ;          
	;.word   0xffff; ????
	.word	0xf020
	.word	0xffff
	
	;call    0(r1)          ;
	.word	0x1291
	.word	0x0000
	
.call0:
	mov     &0x0350,r15     ;0x0350    
	sub     r14,    r15     ;          
	mov.b   r15,    &.data0 ;          
	clr     r2              ;          
	clr     r14             ;
	clr     r15             ;


	;;  halt
	.word	0x3fff	; halt
.exit1:			; should be unreachable
	.word	0x3fff	; halt

;;; but, place your bets on what happens when you run this!!!!!!
