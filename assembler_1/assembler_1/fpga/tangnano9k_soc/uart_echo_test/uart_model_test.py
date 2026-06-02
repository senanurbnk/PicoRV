"""
uart.v cycle-model dogrulamasi (sentez oncesi)
==============================================
iverilog/verilator olmadan UART bit-zamanlamasini dogrulamak icin uart.v'deki
TX ve RX durum makinelerinin BIREBIR Python ikizi. TX cikisini RX girisine
baglayip (loopback) cesitli baytlari gonderir, RX'in geri kurdugunu karsilastirir.

Amac: shift yonu (LSB-first), bit sayisi (10 = start+8+stop), orta-bit ornekleme
ve off-by-one hatalarini sentezden ONCE yakalamak.

NOT: Bu Verilog'un kendisi degil; algoritmanin dogrulanmasidir. Donanim testi
ayrica echo firmware + host_loader --echo-test ile FPGA'de yapilir.
"""

DIV = 8           # kucuk deger -> hizli sim (Verilog'da 2812@9600). Oran onemli, mutlak deger degil.
DIV2 = DIV // 2


class TxModel:
    """uart.v TX FSM ikizi."""
    def __init__(self):
        self.active = False
        self.shift = 0x3FF      # 10-bit, idle hep 1
        self.bitcnt = 0
        self.div = 0

    @property
    def tx(self):
        return 1 if not self.active else (self.shift & 1)

    def start(self, byte):
        # {stop=1, data[7:0], start=0}, tx[0] hatta
        self.shift = (1 << 9) | ((byte & 0xFF) << 1) | 0
        self.bitcnt = 10
        self.div = DIV - 1
        self.active = True

    def tick(self):
        if not self.active:
            return
        if self.div != 0:
            self.div -= 1
        else:
            self.div = DIV - 1
            self.shift = (1 << 9) | (self.shift >> 1)   # sag kaydir, idle=1 doldur
            self.bitcnt -= 1
            if self.bitcnt == 1:
                self.active = False


class RxModel:
    """uart.v RX FSM ikizi (2-FF sync dahil)."""
    def __init__(self):
        self.q = 1
        self.qq = 1
        self.active = False
        self.div = 0
        self.bitcnt = 0
        self.shift = 0
        self.data = None
        self.valid = False

    def tick(self, line):
        # 2-FF senkronizer (önceki degerler kullanilir)
        qq = self.qq
        self.qq = self.q
        self.q = line

        if not self.active:
            if qq == 0:                       # start biti
                self.active = True
                self.div = DIV2 - 1
                self.bitcnt = 0
        else:
            if self.div != 0:
                self.div -= 1
            else:
                self.div = DIV - 1
                if self.bitcnt == 0:
                    self.bitcnt = 1           # start merkezi geçildi
                elif self.bitcnt <= 8:
                    self.shift = ((qq & 1) << 7) | (self.shift >> 1)  # LSB-first
                    self.bitcnt += 1
                else:
                    self.data = self.shift & 0xFF
                    self.valid = True
                    self.active = False


def loopback_byte(byte):
    tx = TxModel()
    rx = RxModel()
    tx.start(byte)
    # Yeterince cycle calistir: 12 bit * DIV + pay
    for _ in range(DIV * 16):
        line = tx.tx
        rx.tick(line)
        tx.tick()
        if rx.valid:
            return rx.data
    return None


def _selftest():
    test_bytes = [0x00, 0xFF, 0xAA, 0x55, 0x01, 0x80, 0x7F, 0x42, ord('A'), ord('Z'), 0x06, 0x15]
    fails = 0
    for b in test_bytes:
        got = loopback_byte(b)
        ok = (got == b)
        if not ok:
            fails += 1
        print(f"  TX 0x{b:02X} -> RX {('0x%02X'%got) if got is not None else 'None':>6}  {'OK' if ok else 'FAIL'}")
    # Ardisik akis: her bayt ayri frame
    assert fails == 0, f"{fails} bayt hatali"
    print("uart_model_test OK: 8N1 LSB-first TX/RX loopback tum baytlarda dogru")


if __name__ == "__main__":
    _selftest()
