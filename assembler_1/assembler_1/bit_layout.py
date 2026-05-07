"""
RV32I Immediate Bit Yerlesim Yardimcilari
==========================================
B-format ve J-format immediate alanlari komut icinde dagitik
yerlestirilir. Hem encoder (komut uretirken) hem linker (relocation
sirasinda mevcut komutu yamarken) ayni dagitim mantigini kullanir;
DRY icin tek modulde toplandi.

Maskeler ilgili immediate alaninin komut icindeki bit konumlarini
tanimlar; relocation patching:
    new_code = (old_code & ~IMM_MASK) | pack_xxx_imm(displacement)
"""


# B-format immediate: bits 31, 30:25, 11:8, 7
B_IMM_MASK = 0xFE000F80

# J-format immediate: bits 31:12 (yani imm[20|10:1|11|19:12])
J_IMM_MASK = 0xFFFFF000

# I-format immediate: bits 31:20
I_IMM_MASK = 0xFFF00000

# S-format immediate: bits 31:25, 11:7
S_IMM_MASK = 0xFE000F80

# U-format immediate: bits 31:12
U_IMM_MASK = 0xFFFFF000


def pack_b_imm(imm):
    """13-bit signed B-type immediate, alt bit (imm[0]) hep 0."""
    imm &= 0x1FFF
    b12  = (imm >> 12) & 0x1
    b11  = (imm >> 11) & 0x1
    b10_5 = (imm >> 5)  & 0x3F
    b4_1  = (imm >> 1)  & 0xF
    return (b12 << 31) | (b10_5 << 25) | (b4_1 << 8) | (b11 << 7)


def pack_j_imm(imm):
    """21-bit signed J-type immediate, alt bit (imm[0]) hep 0."""
    imm &= 0x1FFFFF
    b20    = (imm >> 20) & 0x1
    b10_1  = (imm >> 1)  & 0x3FF
    b11    = (imm >> 11) & 0x1
    b19_12 = (imm >> 12) & 0xFF
    return (b20 << 31) | (b10_1 << 21) | (b11 << 20) | (b19_12 << 12)


def pack_i_imm(imm):
    """12-bit signed I-type immediate (ADDI, LW, ...). Bits 31:20."""
    return (imm & 0xFFF) << 20


def pack_s_imm(imm):
    """12-bit signed S-type immediate (SW, SB). imm[11:5] -> 31:25, imm[4:0] -> 11:7."""
    imm &= 0xFFF
    imm_hi = (imm >> 5) & 0x7F
    imm_lo = imm & 0x1F
    return (imm_hi << 25) | (imm_lo << 7)


def pack_u_imm(imm):
    """20-bit U-type immediate (LUI, AUIPC). Bits 31:12."""
    return (imm & 0xFFFFF) << 12


def read_word_le(buf, offset):
    return (buf[offset] | (buf[offset+1] << 8) |
            (buf[offset+2] << 16) | (buf[offset+3] << 24))


def write_word_le(buf, offset, value):
    value &= 0xFFFFFFFF
    buf[offset+0] =  value        & 0xFF
    buf[offset+1] = (value >> 8)  & 0xFF
    buf[offset+2] = (value >> 16) & 0xFF
    buf[offset+3] = (value >> 24) & 0xFF


def to_signed_bits(value, bits):
    """Iki'nin tumleyeni: dusuk N bit'i isaretli sayi olarak yorumla."""
    mask = (1 << bits) - 1
    value &= mask
    sign_bit = 1 << (bits - 1)
    if value & sign_bit:
        return value - (1 << bits)
    return value


def fits_signed(value, bits):
    """value bits-bit isaretli aralikta mi? Range check."""
    lo = -(1 << (bits - 1))
    hi =  (1 << (bits - 1)) - 1
    return lo <= value <= hi
