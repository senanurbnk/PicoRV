# L-3 Test: pong'u disa acan dosya.
# pong'a BEQZ ile dallanildiktan sonra a0 = 99 yapilir, sonsuz dongude kalinir.

.text
.global pong

pong:
    LI    a0, 99          # ADDI a0, x0, 99 -> 0x06300513
    JAL   x0, pong        # yerel self-loop, reloc yok
