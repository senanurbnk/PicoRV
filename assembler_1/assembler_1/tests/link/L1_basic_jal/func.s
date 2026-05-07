# L-1 Test: Cross-file JAL relocation
# Bu dosya add5'i tanimliyor ve disa aciyor (.global).
# main.o icindeki JAL ra, add5 referansi link sirasinda buraya baglanacak.

.text
.global add5

add5:
    ADDI  a0, a0, 5        # 0x00550513
    RET                    # JALR x0, x1, 0 -> 0x00008067
