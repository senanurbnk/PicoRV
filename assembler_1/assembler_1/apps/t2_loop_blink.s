# T2 — Döngü + LED sayaç/blink (döngü, dallanma, zamanlama)
# Loader 0x3000'e yükler. 6-bit sayaç LED'lerde artar; gecikme döngüsüyle
# görünür hız. Test ettiği: BNE/J döngüsü, ADDI sayaç, gecikme zamanlaması.
# GPIO/LED @ 0x1000_0000 (alt 6 bit).

.text
.global _start

_start:
    LUI   t0, 0x10000        # GPIO/LED base
    LI    t1, 0              # sayaç
loop:
    ANDI  t2, t1, 0x3F       # alt 6 bit -> LED deseni
    SW    t2, 0(t0)          # LED = sayaç[5:0]
    ADDI  t1, t1, 1          # sayaç++
    LUI   t3, 0x8            # gecikme (~); ARTIR -> daha yavaş blink (örn 0x400)
delay:
    ADDI  t3, t3, -1
    BNE   t3, x0, delay
    J     loop
