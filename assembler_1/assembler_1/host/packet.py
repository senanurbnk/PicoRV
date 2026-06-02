"""
Paket cercevelemesi — host ve loader BIREBIR ayni olmali.
=========================================================
Cerceve:
    +-------+-----+-----+-----------+-----------+--------+
    | SYNC  | CMD | LEN |   ADDR    |   DATA    | CRC16  |
    | AA 55 | 1B  | 1B  |  4B (LE)  |  LEN bayt |  2B LE |
    +-------+-----+-----+-----------+-----------+--------+

    CRC16: CRC-16/CCITT-FALSE, SYNC HARIC  CMD..DATA  uzerinden.
    CRC16 tel uzerinde LITTLE-ENDIAN (dusuk bayt once) gonderilir.

Komutlar (CMD):
    0x01 WRITE_BLOCK : DATA'yi ADDR'den itibaren RAM'e yaz
    0x02 START       : ADDR = entry; loader oraya jalr ile atlar (DATA bos)
    0x03 PING        : baglanti testi (DATA bos)

Yanit baytlari:
    0x06 ACK
    0x15 NAK
"""

import struct
from crc import crc16_ccitt

SYNC0, SYNC1 = 0xAA, 0x55

CMD_WRITE_BLOCK = 0x01
CMD_START       = 0x02
CMD_PING        = 0x03

ACK = 0x06
NAK = 0x15

MAX_DATA = 255  # LEN tek bayt


def build_packet(cmd: int, addr: int = 0, data: bytes = b"") -> bytes:
    """Bir cerceve uretir. CRC, CMD..DATA uzerinden hesaplanir."""
    if len(data) > MAX_DATA:
        raise ValueError(f"DATA cok uzun: {len(data)} > {MAX_DATA}")
    body = bytes([cmd & 0xFF, len(data) & 0xFF]) + struct.pack("<I", addr & 0xFFFFFFFF) + data
    crc = crc16_ccitt(body)
    return bytes([SYNC0, SYNC1]) + body + struct.pack("<H", crc)


def parse_packet(frame: bytes):
    """Tam bir cerceveyi cozer. (cmd, addr, data) doner; CRC/sync hatasinda ValueError.
    Loader tarafini test etmek + host self-test icin kullanilir."""
    if len(frame) < 2 + 1 + 1 + 4 + 2:
        raise ValueError("cerceve cok kisa")
    if frame[0] != SYNC0 or frame[1] != SYNC1:
        raise ValueError("SYNC yok")
    cmd = frame[2]
    length = frame[3]
    addr = struct.unpack("<I", frame[4:8])[0]
    data = frame[8:8 + length]
    if len(data) != length:
        raise ValueError(f"DATA eksik: {len(data)} != {length}")
    crc_rx = struct.unpack("<H", frame[8 + length:10 + length])[0]
    body = frame[2:8 + length]
    crc_calc = crc16_ccitt(body)
    if crc_rx != crc_calc:
        raise ValueError(f"CRC uyusmazligi: rx=0x{crc_rx:04X} calc=0x{crc_calc:04X}")
    return cmd, addr, data


def iter_blocks(image: bytes, base_addr: int, block_size: int = 64):
    """Image'i word-hizali (4'un kati) bloklara boler. (addr, chunk) uretir."""
    if block_size % 4 != 0:
        raise ValueError("block_size 4'un kati olmali (word hizasi)")
    for off in range(0, len(image), block_size):
        yield base_addr + off, image[off:off + block_size]


def _selftest():
    # WRITE_BLOCK round-trip
    data = bytes(range(16))
    f = build_packet(CMD_WRITE_BLOCK, 0x3000, data)
    cmd, addr, d = parse_packet(f)
    assert (cmd, addr, d) == (CMD_WRITE_BLOCK, 0x3000, data), (cmd, hex(addr), d)

    # START (bos data)
    f = build_packet(CMD_START, 0x3000)
    cmd, addr, d = parse_packet(f)
    assert cmd == CMD_START and addr == 0x3000 and d == b""

    # Bozuk CRC -> ValueError
    bad = bytearray(build_packet(CMD_WRITE_BLOCK, 0x3000, data))
    bad[-1] ^= 0xFF
    try:
        parse_packet(bytes(bad))
        assert False, "bozuk CRC yakalanmadi"
    except ValueError:
        pass

    # Blok bolme
    img = bytes(range(200))
    blocks = list(iter_blocks(img, 0x3000, 64))
    assert blocks[0][0] == 0x3000 and len(blocks[0][1]) == 64
    assert blocks[-1][0] == 0x3000 + 192 and len(blocks[-1][1]) == 8
    assert b"".join(b for _, b in blocks) == img

    print("packet.py selftest OK (round-trip, START, bozuk-CRC, blok bolme)")


if __name__ == "__main__":
    _selftest()
