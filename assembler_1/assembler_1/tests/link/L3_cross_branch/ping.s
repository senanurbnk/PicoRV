# L-3 Test: Cross-file BRANCH relocation
# BEQZ a0, pong komutu farkli dosyadaki pong etiketine dallanir.
# Linker bunu R_RISCV_BRANCH ile cozecek.

.text
.global _start
.global pong              # extern: pong.s'de tanimli

_start:
    LI    a0, 0           # ADDI a0, x0, 0  -> 0x00000513
    BEQZ  a0, pong        # BEQ  a0, x0, pong (placeholder + reloc)

skip:
    JAL   x0, skip        # 0x0000006F (yerel, reloc yok)
