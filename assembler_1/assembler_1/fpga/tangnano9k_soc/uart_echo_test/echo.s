# Faz 1 — UART Echo Test Firmware
# --------------------------------
# Amac: SoC'a eklenen UART donanimini bring-up etmek. Kendi assembler'imizla
# derlenir, BRAM'e gömülür (mem_init.vh). PicoRV32 reset sonrasi 0x0000'dan baslar.
#
# Davranis: UART'tan gelen her bayti aynen geri yollar (echo).
#   - STATUS.rx_valid (bit0) bekle
#   - DATA oku (rx_valid temizlenir)
#   - STATUS.tx_busy (bit1) bekle
#   - DATA'ya yaz (TX)
#
# UART MMIO: base 0x2000_0000  (+0x00 DATA, +0x04 STATUS)
# Yalnizca desteklenen komut alt kümesi (LUI/LW/ANDI/BEQ/BNE/SW/J).

.text
.global _start

_start:
    LUI   t0, 0x20000         # t0 = 0x20000000  (UART MMIO base)

poll:
    LW    t1, 4(t0)           # t1 = STATUS
    ANDI  t1, t1, 1           # rx_valid?
    BEQ   t1, x0, poll        # gelmemis -> bekle

    LW    t2, 0(t0)           # t2 = DATA (rx byte; okuma rx_valid'i temizler)
    ANDI  t2, t2, 0xFF

tx_wait:
    LW    t3, 4(t0)           # t3 = STATUS
    ANDI  t3, t3, 2           # tx_busy?
    BNE   t3, x0, tx_wait     # mesgul -> bekle

    SW    t2, 0(t0)           # DATA'ya yaz -> TX (echo)
    J     poll
