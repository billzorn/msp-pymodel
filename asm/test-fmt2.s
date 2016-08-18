.section .resetvec, "aw"
.balign 2
	.word	_start

.section .rodata
.balign 2
.ccounter___837:	.word 0
.ccounter___838:	.word 0
.ccounter___839:	.word 0
.ccounter___840:	.word 0
.ccounter___841:	.word 0
.ccounter___842:	.word 0
.ccounter___843:	.word 0
.ccounter___844:	.word 0
.ccounter___845:	.word 0
.ccounter___846:	.word 0
.ccounter___847:	.word 0
.ccounter___848:	.word 0
.ccounter___849:	.word 0
.ccounter___850:	.word 0
.ccounter___851:	.word 0
.ccounter___852:	.word 0
.ccounter___853:	.word 0
.ccounter___854:	.word 0
.ccounter___855:	.word 0
.ccounter___856:	.word 0
.ccounter___857:	.word 0
.ccounter___858:	.word 0
.ccounter___859:	.word 0
.ccounter___860:	.word 0
.ccounter___861:	.word 0
.ccounter___862:	.word 0
.ccounter___863:	.word 0
.ccounter___864:	.word 0
.ccounter___865:	.word 0
.ccounter___866:	.word 0
.ccounter___867:	.word 0
.ccounter___868:	.word 0
.ccounter___869:	.word 0
.ccounter___870:	.word 0
.ccounter___871:	.word 0
.ccounter___872:	.word 0
.ccounter___873:	.word 0
.ccounter___874:	.word 0
.ccounter___875:	.word 0
.ccounter___876:	.word 0
.ccounter___877:	.word 0
.ccounter___878:	.word 0
.ccounter___879:	.word 0
.ccounter___880:	.word 0
.ccounter___881:	.word 0
.ccounter___882:	.word 0
.ccounter___883:	.word 0
.ccounter___884:	.word 0
.ccounter___885:	.word 0
.ccounter___886:	.word 0
.ccounter___887:	.word 0
.ccounter___888:	.word 0
.ccounter___889:	.word 0
.ccounter___890:	.word 0
.ccounter___891:	.word 0
.ccounter___892:	.word 0
.ccounter___893:	.word 0
.ccounter___894:	.word 0
.ccounter___895:	.word 0
.ccounter___896:	.word 0
.ccounter___897:	.word 0
.ccounter___898:	.word 0
.ccounter___899:	.word 0
.ccounter___900:	.word 0
.ccounter___901:	.word 0
.ccounter___902:	.word 0
.ccounter___903:	.word 0
.ccounter___904:	.word 0
.ccounter___905:	.word 0
.ccounter___906:	.word 0
.ccounter___907:	.word 0
.ccounter___908:	.word 0
.ccounter___909:	.word 0
.ccounter___910:	.word 0
.ccounter___911:	.word 0
.ccounter___912:	.word 0
.ccounter___913:	.word 0
.ccounter___914:	.word 0
.ccounter___915:	.word 0
.ccounter___916:	.word 0
.ccounter___917:	.word 0
.ccounter___918:	.word 0
.ccounter___919:	.word 0
.ccounter___920:	.word 0
.ccounter___921:	.word 0
.ccounter___922:	.word 0
.ccounter___923:	.word 0
.ccounter___924:	.word 0
.ccounter___925:	.word 0
.ccounter___926:	.word 0
.ccounter___927:	.word 0
.ccounter___928:	.word 0
.ccounter___929:	.word 0
.ccounter___930:	.word 0
.ccounter___931:	.word 0
.ccounter___932:	.word 0
.ccounter___933:	.word 0
.ccounter___934:	.word 0
.ccounter___935:	.word 0
.ccounter___936:	.word 0

.section .text
.balign 2
.global _start
_start:
	;; disable watchdog timer
	MOV.W	#23168, &0x015C

	;; clear check register
	MOV.W	#0, R13

	;; timer init
	MOV.W	#16, &0x0342
	MOV.W	#512, &0x0340

	;; timer start
	MOV.W	#0, &0x0350
	MOV.W	#-15536, &0x0352
	BIS.W	#16, &0x0340

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___837

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	R10
	RRC	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___838

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	R10
	RRC	R10
	RRC	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___839

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	R10
	RRC	R10
	RRC	R10
	RRC	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___840

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	R10
	RRC	R10
	RRC	R10
	RRC	R10
	RRC	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___841

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___842

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10
	RRC	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___843

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10
	RRC	@R10
	RRC	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___844

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10
	RRC	@R10
	RRC	@R10
	RRC	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___845

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10
	RRC	@R10
	RRC	@R10
	RRC	@R10
	RRC	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___846

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___847

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10+
	RRC	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___848

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10+
	RRC	@R10+
	RRC	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___849

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10+
	RRC	@R10+
	RRC	@R10+
	RRC	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___850

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	@R10+
	RRC	@R10+
	RRC	@R10+
	RRC	@R10+
	RRC	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___851

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___852

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	200(R10)
	RRC	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___853

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	200(R10)
	RRC	200(R10)
	RRC	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___854

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	200(R10)
	RRC	200(R10)
	RRC	200(R10)
	RRC	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___855

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	200(R10)
	RRC	200(R10)
	RRC	200(R10)
	RRC	200(R10)
	RRC	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___856

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___857

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	&0x1c00
	RRC	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___858

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	&0x1c00
	RRC	&0x1c00
	RRC	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___859

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	&0x1c00
	RRC	&0x1c00
	RRC	&0x1c00
	RRC	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___860

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRC	&0x1c00
	RRC	&0x1c00
	RRC	&0x1c00
	RRC	&0x1c00
	RRC	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___861

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___862

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	R10
	SWPB	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___863

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	R10
	SWPB	R10
	SWPB	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___864

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	R10
	SWPB	R10
	SWPB	R10
	SWPB	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___865

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	R10
	SWPB	R10
	SWPB	R10
	SWPB	R10
	SWPB	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___866

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___867

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10
	SWPB	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___868

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10
	SWPB	@R10
	SWPB	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___869

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10
	SWPB	@R10
	SWPB	@R10
	SWPB	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___870

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10
	SWPB	@R10
	SWPB	@R10
	SWPB	@R10
	SWPB	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___871

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___872

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10+
	SWPB	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___873

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10+
	SWPB	@R10+
	SWPB	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___874

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10+
	SWPB	@R10+
	SWPB	@R10+
	SWPB	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___875

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	@R10+
	SWPB	@R10+
	SWPB	@R10+
	SWPB	@R10+
	SWPB	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___876

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___877

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	200(R10)
	SWPB	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___878

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	200(R10)
	SWPB	200(R10)
	SWPB	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___879

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	200(R10)
	SWPB	200(R10)
	SWPB	200(R10)
	SWPB	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___880

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	200(R10)
	SWPB	200(R10)
	SWPB	200(R10)
	SWPB	200(R10)
	SWPB	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___881

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___882

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	&0x1c00
	SWPB	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___883

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	&0x1c00
	SWPB	&0x1c00
	SWPB	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___884

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	&0x1c00
	SWPB	&0x1c00
	SWPB	&0x1c00
	SWPB	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___885

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SWPB	&0x1c00
	SWPB	&0x1c00
	SWPB	&0x1c00
	SWPB	&0x1c00
	SWPB	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___886

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___887

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	R10
	RRA	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___888

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	R10
	RRA	R10
	RRA	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___889

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	R10
	RRA	R10
	RRA	R10
	RRA	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___890

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	R10
	RRA	R10
	RRA	R10
	RRA	R10
	RRA	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___891

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___892

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10
	RRA	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___893

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10
	RRA	@R10
	RRA	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___894

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10
	RRA	@R10
	RRA	@R10
	RRA	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___895

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10
	RRA	@R10
	RRA	@R10
	RRA	@R10
	RRA	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___896

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___897

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10+
	RRA	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___898

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10+
	RRA	@R10+
	RRA	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___899

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10+
	RRA	@R10+
	RRA	@R10+
	RRA	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___900

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	@R10+
	RRA	@R10+
	RRA	@R10+
	RRA	@R10+
	RRA	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___901

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___902

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	200(R10)
	RRA	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___903

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	200(R10)
	RRA	200(R10)
	RRA	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___904

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	200(R10)
	RRA	200(R10)
	RRA	200(R10)
	RRA	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___905

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	200(R10)
	RRA	200(R10)
	RRA	200(R10)
	RRA	200(R10)
	RRA	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___906

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___907

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	&0x1c00
	RRA	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___908

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	&0x1c00
	RRA	&0x1c00
	RRA	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___909

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	&0x1c00
	RRA	&0x1c00
	RRA	&0x1c00
	RRA	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___910

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	RRA	&0x1c00
	RRA	&0x1c00
	RRA	&0x1c00
	RRA	&0x1c00
	RRA	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___911

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___912

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	R10
	SXT	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___913

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	R10
	SXT	R10
	SXT	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___914

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	R10
	SXT	R10
	SXT	R10
	SXT	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___915

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	R10
	SXT	R10
	SXT	R10
	SXT	R10
	SXT	R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___916

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___917

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10
	SXT	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___918

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10
	SXT	@R10
	SXT	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___919

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10
	SXT	@R10
	SXT	@R10
	SXT	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___920

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10
	SXT	@R10
	SXT	@R10
	SXT	@R10
	SXT	@R10
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___921

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___922

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10+
	SXT	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___923

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10+
	SXT	@R10+
	SXT	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___924

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10+
	SXT	@R10+
	SXT	@R10+
	SXT	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___925

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	@R10+
	SXT	@R10+
	SXT	@R10+
	SXT	@R10+
	SXT	@R10+
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___926

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___927

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	200(R10)
	SXT	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___928

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	200(R10)
	SXT	200(R10)
	SXT	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___929

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	200(R10)
	SXT	200(R10)
	SXT	200(R10)
	SXT	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___930

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	200(R10)
	SXT	200(R10)
	SXT	200(R10)
	SXT	200(R10)
	SXT	200(R10)
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___931

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___932

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	&0x1c00
	SXT	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___933

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	&0x1c00
	SXT	&0x1c00
	SXT	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___934

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	&0x1c00
	SXT	&0x1c00
	SXT	&0x1c00
	SXT	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___935

	;;;;;;;;;;;;;;;;

	;; reset gpregs
	MOV.W	#0x1c00, R10
	MOV.W	#0x1c00, R11

	;; save initial
	MOV.W	&0x0350, R14


	;; BEGIN CRITICAL SECTION
	SXT	&0x1c00
	SXT	&0x1c00
	SXT	&0x1c00
	SXT	&0x1c00
	SXT	&0x1c00
	;; END CRITICAL SECTION


	;; save final
	MOV.W	&0x0350, R15

	;; compute cycle count and write to memory
	SUB.W	R14, R15
	MOV.W	R15, &.ccounter___936

	;;;;;;;;;;;;;;;;

.end:
	BR	#.end
