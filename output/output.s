	.def	@feat.00;
	.scl	3;
	.type	0;
	.endef
	.globl	@feat.00
.set @feat.00, 0
	.file	"<string>"
	.def	main;
	.scl	2;
	.type	32;
	.endef
	.text
	.globl	main                            # -- Begin function main
	.p2align	4
main:                                   # @main
# %bb.0:                                # %entry
	subq	$40, %rsp
	leaq	.Lstr(%rip), %rcx
	callq	puts
	xorl	%eax, %eax
	addq	$40, %rsp
	retq
                                        # -- End function
	.section	.rdata,"dr"
.Lstr:                                  # @str
	.asciz	"Hello, World!"

	.addrsig
	.addrsig_sym puts
