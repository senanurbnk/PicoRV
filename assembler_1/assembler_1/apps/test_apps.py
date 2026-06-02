"""
test_apps.py — T1/T2/T3 uygulamalarini ISS'te dogrula (FPGA'siz)
================================================================
Her uygulamayi app.ld (@0x3000) ile derler, ISS'te (tools/iss.py) calistirir,
beklenen LED/davranisi dogrular. T3 icin buton girisi ISS modelinde set edilir.

Calistir (kokten: assembler_1/assembler_1):  python apps/test_apps.py
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from iss import ISS, UartModel

APP_LD = os.path.join(ROOT, "apps", "app.ld")
ENTRY = 0x3000


def build(name):
    out = os.path.join(ROOT, "apps", name)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "run_link.py"),
                        os.path.join(ROOT, "apps", name + ".s"),
                        "-T", APP_LD, "-o", out, "--no-vh"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"{name} build fail:\n{r.stdout}\n{r.stderr}")
    return open(out + ".bin", "rb").read()


def test_t1():
    app = build("t1_arith_led")
    iss = ISS(max_steps=20000)
    iss.load_image(app, base=ENTRY)
    iss.run(entry=ENTRY)
    assert iss.gpio == 42, f"T1 LED beklenen 42, gelen {iss.gpio}"
    print(f"  [OK] T1 arith_led: 40+2 -> LED={iss.gpio} (0b{iss.gpio:06b})")


def test_t2():
    app = build("t2_loop_blink")
    iss = ISS(max_steps=1_000_000)
    iss.load_image(app, base=ENTRY)
    iss.run(entry=ENTRY)
    w = iss.gpio_writes
    assert len(w) >= 6, f"T2 yeterli sayim yok: {w[:10]}"
    assert w[:6] == [0, 1, 2, 3, 4, 5], f"T2 sayac monoton degil: {w[:10]}"
    print(f"  [OK] T2 loop_blink: LED sayaci {w[:8]}... ({len(w)} yazma)")


def test_t3():
    app = build("t3_func_button")
    for btn, expect in ((0, 0x09), (1, 0x3F)):
        iss = ISS(max_steps=20000)
        iss.load_image(app, base=ENTRY)
        iss.button = btn
        iss.run(entry=ENTRY)
        assert iss.gpio == expect, \
            f"T3 buton={btn} LED beklenen 0x{expect:02X}, gelen 0x{iss.gpio:02X}"
        print(f"  [OK] T3 func_button: buton={btn} -> LED=0b{iss.gpio:06b} "
              f"(get_button() JAL/RET + GPIO girisi)")


if __name__ == "__main__":
    print("=== T1/T2/T3 uygulama dogrulamasi (ISS, FPGA'siz) ===")
    test_t1()
    test_t2()
    test_t3()
    print("TUM UYGULAMA TESTLERI GECTI")
