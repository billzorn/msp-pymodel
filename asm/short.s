.section .resetvec, "aw"
.balign 2
	.word	0x4406

.section .text
.balign 2
	MOV	#23168, &0x015c

	;; test code here!

	mov     #8350,  r1 ;#0x209e
	mov     #3836,  r5 ;#0x0efc
	sub.b   @r1+,   3690(r5) ; 0x0e6a
	mov     #8943,  r4	;#0x22ef
	mov     #273,   r5	;#0x0111
	sub     @r4+,   8423(r5) ; 0x20e7
	mov     #7184,  r1	;#0x1c10
	sub     @r1+,   r5	;
	mov     #8944,  r4	;#0x22f0
	sub.b   @r4+,   r5	;
	
	mov     #8334,  r1	;#0x208e
	sub     @r1+,   300	; PC rel. ???

	mov     #7819,  r4	;#0x1e8b
	sub     @r4+,   300	; PC rel. ???

	;; had a bug
	mov     #7545,  r1	#0x1d79
	sub     @r1+,   &0x2175	
	
	mov     #8240,  r4	;#0x2030
	sub     @r4+,   &0x1da7	;
	
	.word	0x3fff	; halt
	.word	0x3fff	; halt
