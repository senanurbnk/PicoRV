# Tang Nano 9K + PicoRV32 — delay.s
# ----------------------------------
# Basit busy-wait gecikme dongusu. Yaklasik LUI ile yuklenen
# sayim degeri kadar iterasyon yapar.
#
# Calculation @ 27 MHz, picorv32 ~4-6 cycle/instruction:
#   0x100000 iter * (ADDI + BNE = ~10 cycle) / 27e6 ≈ 0.39 sn
#
# Leaf fonksiyon: ra dokunulmaz, ek register kaydetmeye gerek yok.

.text
.global delay_loop

delay_loop:
    LUI   t2, 0x100         # t2 = 0x00100000  (~1M iterasyon)
spin:
    ADDI  t2, t2, -1
    BNE   t2, x0, spin
    RET                     # JALR x0, x1, 0
