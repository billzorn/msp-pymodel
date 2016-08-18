    ;; 6082:       34 40 10 1d     mov     #7440,  r4      ;#0x1d10
    ;; 6086:       b2 40 50 1d     mov     #7504,  &0x1d10 ;#0x1d50
    ;; 608a:       10 1d 
    ;; 608c:       b2 40 00 00     mov     #0,     &0x1d12 ;
    ;; 6090:       12 1d 
    ;; 6092:       1e 42 50 03     mov     &0x0350,r14     ;0x0350
    ;; 6096:       b4 64 00 00     addc    @r4+,   0(r4)   ;
    ;; 609a:       10 84 00 00     sub     0(r4),  r0      ;
    ;; 609e:       1f 42 50 03     mov     &0x0350,r15     ;0x0350
    ;; 60a2:       0f 8e           sub     r14,    r15     ;
    ;; 60a4:       c2 4f 83 44     mov.b   r15,    &0x4483 ;
    ;; 60a8:       82 43 10 1d     mov     #0,     &0x1d10 ;r3 As==00
    ;; 60ac:       02 43           clr     r2              ;
    ;; 60ae:       0e 43           clr     r14             ;
    ;; 60b0:       0f 43           clr     r15             ;


.section .resetvec, "aw"
.balign 2
	.word	0x4406

.section .text
.balign 2
	MOV	#23168, &0x015c

	jmp	.go
	.word	0x3fff
.go:

	mov     #7440,  r4
	mov     #7504,  &0x1d10
	mov     #0,     &0x1d12
	mov     &0x0350,r14
	addc    @r4+,   0(r4)
	sub     0(r4),  r0
	mov     &0x0350,r15
	sub     r14,    r15
	mov.b   r15,    &0x4400
	mov     #0,     &0x1d10
	clr     r2
	clr     r14
	clr     r15
	
	.word	0x3fff	; halt
	.word	0x3fff	; halt
