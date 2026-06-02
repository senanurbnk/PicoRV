"""
test_loader.py — loader.s'i ISS uzerinde host paketleriyle dogrula (FPGA'siz)
=============================================================================
GERCEK loader makine kodunu (kendi linker'imizin urettigi loader.bin) bir
RV32I komut-set simulatorunde (tools/iss.py) calistirir. Host (host/packet.py)
WRITE_BLOCK + START paketleri uretir; loader bunlari UART'tan okur, CRC dogrular,
uygulamayi 0x3000'e yazar, ACK gonderir ve uygulamaya atlar.

Bu, sentez OLMADAN loader'in komut akisini, CRC'sini (host crc.py ile birebir),
bellek yazimini, ACK/NAK'ini ve jump'ini kanitlar.

Calistir: python loader/test_loader.py   (proje kokunden: assembler_1/assembler_1)
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # assembler_1/assembler_1
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "host"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from packet import build_packet, iter_blocks, CMD_WRITE_BLOCK, CMD_START, ACK, NAK
from iss import ISS, UartModel

APP_ENTRY = 0x3000


def _build(src, ld, out):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "run_link.py"),
                        src, "-T", ld, "-o", out, "--no-vh"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"build fail {src}:\n{r.stdout}\n{r.stderr}")
    with open(out + ".bin", "rb") as f:
        return f.read()


def _make_stream(app, base, block_size=16, corrupt_first=False):
    """Host'un gonderecegi bayt akisini uret. corrupt_first: ilk WRITE paketinin
    CRC'sini boz + ardindan duzgun halini ekle (retransmit senaryosu)."""
    stream = bytearray()
    blocks = list(iter_blocks(app, base, block_size))
    for i, (addr, chunk) in enumerate(blocks):
        pkt = build_packet(CMD_WRITE_BLOCK, addr, chunk)
        if corrupt_first and i == 0:
            bad = bytearray(pkt); bad[-1] ^= 0xFF      # CRC son baytini boz
            stream += bad                              # loader NAK vermeli
            stream += pkt                              # host retransmit (dogru)
        else:
            stream += pkt
    stream += build_packet(CMD_START, base)
    return bytes(stream), len(blocks)


def test_load_and_jump():
    loader = _build(os.path.join(ROOT, "loader/loader.s"),
                    os.path.join(ROOT, "loader/loader.ld"),
                    os.path.join(ROOT, "loader/loader"))
    app = _build(os.path.join(ROOT, "apps/t1_arith_led.s"),
                 os.path.join(ROOT, "apps/app.ld"),
                 os.path.join(ROOT, "apps/t1_arith_led"))
    print(f"loader.bin={len(loader)}B  t1.bin={len(app)}B")

    stream, nblocks = _make_stream(app, APP_ENTRY, block_size=16)
    uart = UartModel(rx_bytes=stream)
    iss = ISS(uart=uart, max_steps=2_000_000)
    iss.load_image(loader, base=0)
    reason = iss.run(entry=0, stop_on_pc=APP_ENTRY)

    # 1) Loader uygulamaya atladi mi?
    assert reason == "stop_on_pc" and iss.pc == APP_ENTRY, \
        f"jump fail: reason={reason} pc=0x{iss.pc:X}"
    # 2) RAM'deki uygulama gonderilenle birebir mi? (endianness dahil)
    ram = bytes(iss.mem[APP_ENTRY:APP_ENTRY + len(app)])
    assert ram == app, f"RAM mismatch:\n  got {ram.hex()}\n  exp {app.hex()}"
    # 3) Her WRITE blogu icin bir ACK (START'a yanit yok)
    assert bytes(uart.tx) == bytes([ACK] * nblocks), \
        f"ACK beklenen {nblocks}, gelen tx={bytes(uart.tx).hex()}"
    print(f"  [OK] load+jump: {nblocks} blok ACK'lendi, RAM birebir, pc->0x{APP_ENTRY:X}")


def test_run_app_after_jump():
    """Loader jump ettikten SONRA uygulama gercekten kosuyor mu? (LED=42)"""
    loader = _build(os.path.join(ROOT, "loader/loader.s"),
                    os.path.join(ROOT, "loader/loader.ld"),
                    os.path.join(ROOT, "loader/loader"))
    app = _build(os.path.join(ROOT, "apps/t1_arith_led.s"),
                 os.path.join(ROOT, "apps/app.ld"),
                 os.path.join(ROOT, "apps/t1_arith_led"))
    stream, _ = _make_stream(app, APP_ENTRY, block_size=16)
    uart = UartModel(rx_bytes=stream)
    iss = ISS(uart=uart, max_steps=2_000_000)
    iss.load_image(loader, base=0)
    iss.run(entry=0)                       # stop yok: app spin'e girer, max_steps'te durur
    assert iss.gpio == 42, f"LED beklenen 42, gelen {iss.gpio}"
    print(f"  [OK] jump sonrasi uygulama kostu: GPIO/LED = {iss.gpio} (0b{iss.gpio:06b})")


def test_nak_then_retransmit():
    """Bozuk CRC -> loader NAK; host retransmit -> ACK; RAM yine dogru."""
    loader = _build(os.path.join(ROOT, "loader/loader.s"),
                    os.path.join(ROOT, "loader/loader.ld"),
                    os.path.join(ROOT, "loader/loader"))
    app = _build(os.path.join(ROOT, "apps/t1_arith_led.s"),
                 os.path.join(ROOT, "apps/app.ld"),
                 os.path.join(ROOT, "apps/t1_arith_led"))
    stream, nblocks = _make_stream(app, APP_ENTRY, block_size=16, corrupt_first=True)
    uart = UartModel(rx_bytes=stream)
    iss = ISS(uart=uart, max_steps=2_000_000)
    iss.load_image(loader, base=0)
    reason = iss.run(entry=0, stop_on_pc=APP_ENTRY)
    assert reason == "stop_on_pc", f"jump fail: {reason}"
    ram = bytes(iss.mem[APP_ENTRY:APP_ENTRY + len(app)])
    assert ram == app, "RAM mismatch (retransmit sonrasi)"
    # ilk yanit NAK, sonra nblocks ACK
    expected = bytes([NAK] + [ACK] * nblocks)
    assert bytes(uart.tx) == expected, \
        f"NAK/ACK dizisi beklenen {expected.hex()}, gelen {bytes(uart.tx).hex()}"
    print(f"  [OK] bozuk CRC -> NAK, retransmit -> {nblocks}x ACK, RAM birebir")


if __name__ == "__main__":
    print("=== loader.s ISS dogrulamasi (FPGA'siz, gercek makine kodu) ===")
    test_load_and_jump()
    test_run_app_after_jump()
    test_nak_then_retransmit()
    print("TUM LOADER TESTLERI GECTI")
