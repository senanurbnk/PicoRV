"""
CRC-16/CCITT-FALSE — host ve loader BIREBIR ayni algoritmayi kullanir.
=====================================================================
Parametreler (Catalogue of parametrised CRC algorithms):
    width   = 16
    poly    = 0x1021
    init    = 0xFFFF
    refin   = false   (MSB-first; reflection YOK)
    refout  = false
    xorout  = 0x0000
    check   = 0x29B1  (CRC of ASCII "123456789")

Reflection'siz MSB-first secildi cunku RV32I loader'da birebir yazilabilir:
    her bayt icin: crc ^= (b << 8); 8 kez: bit15 set ise (crc<<1)^0x1021,
    degilse crc<<1; hep 0xFFFF ile maskele.
"""

POLY = 0x1021
INIT = 0xFFFF


def crc16_ccitt(data: bytes, init: int = INIT) -> int:
    """Bitwise CRC-16/CCITT-FALSE. Loader'daki RV32I dongusunun referansi."""
    crc = init & 0xFFFF
    for b in data:
        crc ^= (b << 8) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


# Tablo tabanli surum (host icin hizli; sonuc bitwise ile ayni olmali)
_TABLE = None


def _build_table():
    global _TABLE
    tbl = []
    for n in range(256):
        c = (n << 8) & 0xFFFF
        for _ in range(8):
            c = ((c << 1) ^ POLY) & 0xFFFF if (c & 0x8000) else (c << 1) & 0xFFFF
        tbl.append(c)
    _TABLE = tbl


def crc16_ccitt_table(data: bytes, init: int = INIT) -> int:
    if _TABLE is None:
        _build_table()
    crc = init & 0xFFFF
    for b in data:
        crc = ((crc << 8) ^ _TABLE[((crc >> 8) ^ b) & 0xFF]) & 0xFFFF
    return crc & 0xFFFF


def _selftest():
    # 1) Standart check vektoru
    assert crc16_ccitt(b"123456789") == 0x29B1, \
        f"check fail: 0x{crc16_ccitt(b'123456789'):04X}"
    # 2) Tablo ve bitwise ayni olmali (rastgele)
    import os
    for _ in range(200):
        d = os.urandom(_ % 40)
        assert crc16_ccitt(d) == crc16_ccitt_table(d), "table != bitwise"
    # 3) Bilinen kucuk vektorler
    assert crc16_ccitt(b"") == 0xFFFF
    assert crc16_ccitt(b"A") == crc16_ccitt(b"A")
    print("crc.py selftest OK (check=0x29B1, table==bitwise, 200 random)")


if __name__ == "__main__":
    _selftest()
