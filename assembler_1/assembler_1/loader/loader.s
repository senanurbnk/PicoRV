# =============================================================
# loader.s — PicoRV32 RV32I Yazilimsal Bootstrap Loader (Proje 3)
# =============================================================
# Hocanin istegi: loader PicoRV'nin KENDI komut setiyle yazilir ve
# kendi assembler+linker'imizla derlenir. Reset sonrasi 0x0000'dan
# baslar, UART'tan paket alir, CRC-16/CCITT-FALSE ile dogrular,
# uygulamayi hedef adrese yazar, START komutunda uygulamaya atlar.
#
# Paket (host/packet.py ile BIREBIR):
#   SYNC(0xAA 0x55) | CMD | LEN | ADDR(4 LE) | DATA(LEN) | CRC16(2 LE)
#   CRC: CMD..DATA uzerinden, CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)
#   CMD: 0x01 WRITE_BLOCK, 0x02 START(jump), 0x03 PING
#   Yanit: 0x06 ACK / 0x15 NAK
#
# MMIO: UART base 0x2000_0000 (+0x00 DATA, +0x04 STATUS[0]=rx_valid,[1]=tx_busy)
#
# Register kullanimi (s* kalici; leaf'ler yalniz t*/a0/ra kullanir):
#   s0=UART base  s1=crc  s2=cmd  s3=len  s4=addr  s5=rx_crc  s6=i  s7=wptr
# Leaf altprogramlar (getc/putc/crc16_byte) baska altprogram CAGIRMAZ;
# bu yuzden tek seviye 'ra' yeter, stack gerekmez.
#
# Yalnizca desteklenen 23-komut alt kumesi kullanilir.

.text
.global _start

_start:
    LUI   s0, 0x20000          # s0 = 0x2000_0000 (UART base)

main_loop:
    # ---- SYNC: 0xAA 0x55 ----
find_aa:
    CALL  getc
    LI    t0, 0xAA
    BNE   a0, t0, find_aa
    CALL  getc
    LI    t0, 0x55
    BNE   a0, t0, find_aa      # 0x55 degilse sync'i yeniden ara

    # ---- crc = 0xFFFF ----
    LUI   s1, 0x10
    ADDI  s1, s1, -1           # s1 = 0x0000FFFF

    # ---- CMD ----
    CALL  getc
    MV    s2, a0
    CALL  crc16_byte

    # ---- LEN ----
    CALL  getc
    MV    s3, a0
    CALL  crc16_byte

    # ---- ADDR (4 bayt, little-endian) -> s4 ----
    CALL  getc
    MV    s4, a0               # byte0
    CALL  crc16_byte
    CALL  getc
    SLLI  t0, a0, 8
    OR    s4, s4, t0           # byte1
    CALL  crc16_byte
    CALL  getc
    SLLI  t0, a0, 16
    OR    s4, s4, t0           # byte2
    CALL  crc16_byte
    CALL  getc
    SLLI  t0, a0, 24
    OR    s4, s4, t0           # byte3
    CALL  crc16_byte

    # ---- DATA (s3 bayt) -> [s4 + i], CRC'ye kat ----
    LI    s6, 0                # i = 0
    MV    s7, s4               # wptr = addr
data_loop:
    BEQ   s6, s3, data_done
    CALL  getc
    SB    a0, 0(s7)            # uygulamayi RAM'e yaz
    CALL  crc16_byte
    ADDI  s7, s7, 1
    ADDI  s6, s6, 1
    J     data_loop
data_done:

    # ---- CRC16 (2 bayt LE) -> s5 ----
    CALL  getc
    MV    s5, a0               # crc lo
    CALL  getc
    SLLI  t0, a0, 8
    OR    s5, s5, t0           # s5 = lo | hi<<8

    # ---- karsilastir ----
    BNE   s1, s5, send_nak

    # CRC dogru: START ise atla, degilse ACK
    LI    t0, 0x02
    BEQ   s2, t0, do_jump
    LI    a0, 0x06             # ACK
    CALL  putc
    J     main_loop

send_nak:
    LI    a0, 0x15             # NAK
    CALL  putc
    J     main_loop

do_jump:
    JALR  x0, s4, 0            # uygulamaya devret (entry = addr)

# -------------------------------------------------------------
# getc: UART'tan bir bayt oku -> a0  (leaf)
# -------------------------------------------------------------
getc:
    LW    t1, 4(s0)           # STATUS
    ANDI  t1, t1, 1           # rx_valid?
    BEQ   t1, x0, getc        # gelmemis -> bekle
    LW    a0, 0(s0)           # DATA (okuma rx_valid'i temizler)
    ANDI  a0, a0, 0xFF
    RET

# -------------------------------------------------------------
# putc: a0'i UART'a yaz  (leaf)
# -------------------------------------------------------------
putc:
    LW    t1, 4(s0)           # STATUS
    ANDI  t1, t1, 2           # tx_busy?
    BNE   t1, x0, putc        # mesgul -> bekle
    SW    a0, 0(s0)           # DATA -> TX
    RET

# -------------------------------------------------------------
# crc16_byte: s1 = CRC16_CCITT_update(s1, a0)   (leaf)
#   host/crc.py crc16_ccitt ile BIREBIR (MSB-first, poly 0x1021)
# -------------------------------------------------------------
crc16_byte:
    SLLI  t0, a0, 8           # byte << 8
    XOR   s1, s1, t0          # crc ^= byte<<8
    LUI   t1, 0x10
    ADDI  t1, t1, -1          # t1 = 0xFFFF (maske)
    AND   s1, s1, t1
    LI    t2, 8               # 8 bit
crc_loop:
    LUI   t3, 0x8             # 0x8000
    AND   t0, s1, t3          # crc & 0x8000
    SLLI  s1, s1, 1           # crc <<= 1
    BEQ   t0, x0, crc_skip
    LUI   t3, 0x1
    ADDI  t3, t3, 0x21        # t3 = 0x1021
    XOR   s1, s1, t3          # crc ^= 0x1021
crc_skip:
    AND   s1, s1, t1          # crc &= 0xFFFF
    ADDI  t2, t2, -1
    BNE   t2, x0, crc_loop
    RET
