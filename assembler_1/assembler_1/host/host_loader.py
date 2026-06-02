"""
host_loader.py — PC tarafi UART yukleyici
==========================================
run_link.py'in urettigi app.bin'i FPGA'deki loader'a seri porttan yukler.

Kullanim:
    python host_loader.py --port COM5 --baud 9600  --bin app.bin --addr 0x3000 --entry 0x3000
    python host_loader.py --port COM5 --ping                     # Faz 1 baglanti testi
    python host_loader.py --selftest                             # FPGA'siz: crc+packet dogrula

Akis:
    1. app.bin oku
    2. word-hizali bloklara bol
    3. her blok -> WRITE_BLOCK paketi -> gonder -> ACK bekle (NAK'ta retry)
    4. tum bloklar bitince START(entry) paketi
    5. (metrik) toplam yukleme suresi

Bagimlilik: pyserial (host/requirements.txt)
"""

import argparse
import sys
import time

from packet import (
    build_packet, iter_blocks,
    CMD_WRITE_BLOCK, CMD_START, CMD_PING,
    ACK, NAK,
)


def _open_serial(port, baud, timeout):
    try:
        import serial  # pyserial
    except ImportError:
        print("HATA: pyserial yok. 'pip install -r host/requirements.txt'", file=sys.stderr)
        raise
    return serial.Serial(port=port, baudrate=baud, timeout=timeout)


def _wait_ack(ser, timeout):
    """Tek bayt yanit bekler. ACK/NAK/None(timeout) doner."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        b = ser.read(1)
        if b:
            return b[0]
    return None


def send_block(ser, addr, data, retries, timeout, verbose=False):
    pkt = build_packet(CMD_WRITE_BLOCK, addr, data)
    for attempt in range(1, retries + 1):
        ser.write(pkt)
        resp = _wait_ack(ser, timeout)
        if resp == ACK:
            if verbose:
                print(f"  0x{addr:08X} +{len(data):3d}B -> ACK (deneme {attempt})")
            return True
        if verbose:
            r = "NAK" if resp == NAK else ("timeout" if resp is None else f"0x{resp:02X}")
            print(f"  0x{addr:08X} +{len(data):3d}B -> {r}, yeniden ({attempt}/{retries})")
    return False


def load_image(ser, image, base_addr, entry, block_size, retries, timeout, verbose=False):
    t0 = time.time()
    nblocks = 0
    for addr, chunk in iter_blocks(image, base_addr, block_size):
        if not send_block(ser, addr, chunk, retries, timeout, verbose):
            print(f"HATA: 0x{addr:08X} blogu {retries} denemede yuklenemedi", file=sys.stderr)
            return False, time.time() - t0
        nblocks += 1
    # START
    ser.write(build_packet(CMD_START, entry))
    elapsed = time.time() - t0
    print(f"Yuklendi: {len(image)} bayt, {nblocks} blok, {elapsed*1000:.1f} ms; "
          f"START -> entry 0x{entry:08X}")
    return True, elapsed


def do_ping(ser, timeout):
    ser.write(build_packet(CMD_PING))
    resp = _wait_ack(ser, timeout)
    if resp == ACK:
        print("PING -> ACK (baglanti OK)")
        return True
    print(f"PING -> {'NAK' if resp==NAK else 'timeout/yanitsiz'}", file=sys.stderr)
    return False


def do_echo_test(ser, timeout):
    """Faz 1 bring-up: FPGA'deki echo firmware'i ile raw bayt echo dogrula.
    (Henuz loader/paket yok; sadece UART donanimi sinanir.)"""
    payload = bytes(range(256))   # 0x00..0xFF — tum bayt desenleri
    ser.reset_input_buffer()
    ser.write(payload)
    got = bytearray()
    deadline = time.time() + max(timeout, len(payload) * 0.02 + 1.0)
    while len(got) < len(payload) and time.time() < deadline:
        chunk = ser.read(len(payload) - len(got))
        if chunk:
            got.extend(chunk)
    if bytes(got) == payload:
        print(f"ECHO TEST OK: {len(payload)} bayt (0x00..0xFF) birebir geri geldi")
        return True
    print(f"ECHO TEST FAIL: gonderilen {len(payload)}B, gelen {len(got)}B", file=sys.stderr)
    # ilk farki bildir
    for i in range(min(len(got), len(payload))):
        if got[i] != payload[i]:
            print(f"  ilk fark index {i}: gonderilen 0x{payload[i]:02X}, gelen 0x{got[i]:02X}",
                  file=sys.stderr)
            break
    return False


def main():
    ap = argparse.ArgumentParser(description="PicoRV32 UART loader (host)")
    ap.add_argument("--port", help="Seri port (COM5, /dev/ttyUSB0)")
    ap.add_argument("--baud", type=int, default=9600, help="Baud (bring-up: 9600)")
    ap.add_argument("--bin", help="Yuklenecek app .bin")
    ap.add_argument("--addr", type=lambda x: int(x, 0), default=0x3000, help="Yukleme base adresi")
    ap.add_argument("--entry", type=lambda x: int(x, 0), default=0x3000, help="START entry adresi")
    ap.add_argument("--block-size", type=int, default=64, help="Blok boyu (4'un kati)")
    ap.add_argument("--retries", type=int, default=5)
    ap.add_argument("--timeout", type=float, default=2.0, help="Yanit timeout (s)")
    ap.add_argument("--ping", action="store_true", help="Sadece PING gonder (loader gerekir)")
    ap.add_argument("--echo-test", action="store_true",
                    help="Faz 1: echo firmware ile raw bayt echo dogrula")
    ap.add_argument("--selftest", action="store_true", help="FPGA'siz crc+packet self-test")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        import crc, packet
        crc._selftest()
        packet._selftest()
        print("host_loader selftest OK")
        return 0

    if not args.port:
        ap.error("--port gerekli (veya --selftest)")

    ser = _open_serial(args.port, args.baud, args.timeout)
    try:
        if args.echo_test:
            return 0 if do_echo_test(ser, args.timeout) else 1
        if args.ping:
            return 0 if do_ping(ser, args.timeout) else 1
        if not args.bin:
            ap.error("--bin gerekli (veya --ping)")
        with open(args.bin, "rb") as f:
            image = f.read()
        ok, _ = load_image(ser, image, args.addr, args.entry,
                           args.block_size, args.retries, args.timeout, args.verbose)
        return 0 if ok else 1
    finally:
        ser.close()


if __name__ == "__main__":
    raise SystemExit(main())
