# T1 — Aritmetik + LED (en basit yükleme kanıtı)
# Loader bunu 0x3000'e yükleyip jump eder. Sonuc LED'lerde görünür.
# 40 + 2 = 42 = 0x2A = 0b101010 -> LED desenleri.
# GPIO @ 0x1000_0000 (alt 6 bit -> LED).

.text
.global _start

_start:
    LUI   t0, 0x10000        # t0 = 0x1000_0000 (GPIO/LED base)
    LI    t1, 40
    LI    t2, 2
    ADD   t3, t1, t2         # t3 = 42
    SW    t3, 0(t0)          # LED = 42 (0b101010)
spin:
    J     spin               # uygulama burada doner (gozlem icin)
