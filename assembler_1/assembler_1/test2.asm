# Test 2: Tüm 20 komutun ve pseudo-komutların testi
# Açıklama: Her komut tipini (R, I, S, B, U, J) ve
#            pseudo-komutları (NOP, LI, MV, RET) kapsayan kapsamlı test.

.text

main:    LUI   t0, 0x10000       # U-type: t0 = 0x10000000

         # I-type aritmetik
         ADDI  a0, zero, 100     # a0 = 100
         ADDI  a1, zero, 200     # a1 = 200

         # R-type
         ADD   a2, a0, a1        # a2 = 300
         SUB   a3, a1, a0        # a3 = 100
         AND   a4, a0, a1        # a4 = a0 & a1
         OR    a5, a0, a1        # a5 = a0 | a1
         SLT   a6, a0, a1        # a6 = (a0 < a1) ? 1 : 0

         # I-type (immediate işlemler)
         ANDI  a7, a0, 0xFF      # a7 = a0 & 0xFF
         SLLI  t1, a0, 2         # t1 = a0 << 2
         SRLI  t2, a1, 3         # t2 = a1 >> 3

         # I-type yükleme
         LW    t3, 0(sp)         # t3 = mem[sp]
         LB    t4, 4(sp)         # t4 = sign_ext(mem[sp+4])

         # S-type kaydetme
         SW    a2, 8(sp)         # mem[sp+8] = a2
         SB    a3, 12(sp)        # mem[sp+12] = a3[7:0]

         # B-type dallanma
         BEQ   a0, a1, skip      # a0 == a1 ise skip'e atla
         BLT   a0, a1, skip      # a0 <  a1 ise skip'e atla
         ADDI  a0, a0, 1         # a0 = a0 + 1 (atlama olmadıysa)

skip:    JAL   ra, func          # J-type: func'ı çağır, dönüş adresini ra'ya kaydet

         # Pseudo-komutlar
         NOP                     # ADDI x0, x0, 0
         LI    t5, 42            # ADDI t5, x0, 42
         MV    t6, a0            # ADDI t6, a0, 0
         RET                     # JALR x0, ra, 0

# ── Alt program (fonksiyon) ──
func:    ADDI  sp, sp, -4        # yığın çerçevesi aç
         SW    ra, 0(sp)         # dönüş adresini yığına kaydet
         LW    ra, 0(sp)         # dönüş adresini yığından yükle
         ADDI  sp, sp, 4         # yığın çerçevesini kapat
         JALR  zero, ra, 0       # I-type: ra adresine dön