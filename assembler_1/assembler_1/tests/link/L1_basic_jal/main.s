# L-1 Test: Cross-file JAL relocation
# Bu dosya add5 sembolune referans veriyor ama tanimlamiyor.
# Linker, R_RISCV_JAL relocation'i ile bu referansi func.o icindeki add5'e baglamali.

.text
.global _start
.global add5             # disa baglanacak (linker cozecek)

_start:
    LI    a0, 10           # ADDI a0, x0, 10  -> 0x00A00513
    JAL   ra, add5         # External symbol -> placeholder 0x000000EF + reloc

done:
    JAL   x0, done         # Local self-loop -> 0x0000006F (cozuldu, reloc yok)
