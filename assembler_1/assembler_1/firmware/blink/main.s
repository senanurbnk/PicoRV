# Tang Nano 9K + PicoRV32 — LED Counter Demo (main.s)
# ----------------------------------------------------
# Cross-file CALL ile delay_loop'a dallanir; bu, linker'in
# R_RISCV_JAL relocation'unu gercek bir SoC uzerinde test eder.
#
# Bellek haritasi:
#   0x00000000 - 0x00001FFF   .text  (BRAM, picorv32 reset PC=0)
#   0x10000000                 GPIO   (alt 6 bit -> LED0..LED5)

.text
.global _start
.global delay_loop          # extern: delay.s'de tanimli

_start:
    LUI   t0, 0x10000       # t0 = 0x10000000  (GPIO MMIO base)
    LI    t1, 0             # t1 = 0           (sayac)

loop:
    SW    t1, 0(t0)         # *(GPIO) = sayac  -> LED'ler
    ADDI  t1, t1, 1         # sayac++
    CALL  delay_loop        # JAL ra, delay_loop  -> R_RISCV_JAL reloc
    J     loop              # JAL x0, loop        -> yerel, reloc yok
