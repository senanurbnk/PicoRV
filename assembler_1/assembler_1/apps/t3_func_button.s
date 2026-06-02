# T3 — Alt program çağrısı + buton girişi (en karmaşık test)
# Loader 0x3000'e yükler. get_button alt programını JAL/RET ile çağırır;
# butona göre LED desenini değiştirir.
# Test ettiği: fonksiyon çağrısı (JAL/JALR ret), PC-bağıl offset, GPIO GİRİŞİ,
# koşullu dallanma.
#
# GPIO @ 0x1000_0000:  +0x00 = LED çıkış,  +0x04 = buton (bit0, 1=basılı)

.text
.global _start

_start:
    LUI   s0, 0x10000        # GPIO base 0x1000_0000

main:
    CALL  get_button         # a0 = buton durumu (0/1)
    BEQ   a0, x0, released
    LI    t1, 0x3F           # BASILI -> tüm 6 LED yanar (0b111111)
    J     show
released:
    LI    t1, 0x09           # BIRAKILDI -> desen 0b001001
show:
    SW    t1, 0(s0)          # LED = desen
    J     main

# get_button: buton durumunu oku -> a0  (leaf altprogram)
get_button:
    LW    a0, 4(s0)          # GPIO+4 = buton
    ANDI  a0, a0, 1
    RET
