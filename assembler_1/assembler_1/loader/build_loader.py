"""
build_loader.py — loader.s'i derle ve SoC BRAM init dosyalarini uret
=====================================================================
Zincir: loader.s -> (assembler) -> loader.o.json -> (linker) -> loader.bin/.hex
        -> loader_init.vh  (Verilog `include header)

Uretilen loader_init.vh + loader.hex SoC klasorune (fpga/tangnano9k_soc/) yazilir.
Loader'i BRAM boot firmware'i yapmak icin (echo bring-up bittikten SONRA):

    python loader/build_loader.py            # loader_init.vh + loader.hex uretir
    cp fpga/tangnano9k_soc/loader_init.vh  fpga/tangnano9k_soc/mem_init.vh
    cp fpga/tangnano9k_soc/loader.hex      fpga/tangnano9k_soc/mem.hex
    # sonra Gowin: Run All -> Programmer

`--install` ile mem_init.vh/mem.hex dogrudan loader'a cevrilir (echo'nun yerini alir).
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # assembler_1/assembler_1
SOC  = os.path.join(ROOT, "fpga", "tangnano9k_soc")


def main():
    ap = argparse.ArgumentParser(description="Loader derle + SoC init uret")
    ap.add_argument("--install", action="store_true",
                    help="mem_init.vh/mem.hex'i dogrudan loader'a cevir (echo'nun yerini alir)")
    args = ap.parse_args()

    out = os.path.join(ROOT, "loader", "loader")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "run_link.py"),
                        os.path.join(ROOT, "loader", "loader.s"),
                        "-T", os.path.join(ROOT, "loader", "loader.ld"),
                        "-o", out, "-v"], cwd=ROOT)
    if r.returncode != 0:
        return r.returncode

    # SoC klasorune kopyala (mem_init.vh'yi ezmeden, ayri dosya olarak)
    shutil.copy(out + "_init.vh", os.path.join(SOC, "loader_init.vh"))
    shutil.copy(out + ".hex",     os.path.join(SOC, "loader.hex"))
    print(f"  -> {os.path.join(SOC, 'loader_init.vh')}")
    print(f"  -> {os.path.join(SOC, 'loader.hex')}")

    if args.install:
        shutil.copy(out + "_init.vh", os.path.join(SOC, "mem_init.vh"))
        shutil.copy(out + ".hex",     os.path.join(SOC, "mem.hex"))
        print("  [install] mem_init.vh/mem.hex artik LOADER (boot firmware = loader)")
    else:
        print("  (Aktif etmek icin: loader_init.vh -> mem_init.vh, loader.hex -> mem.hex"
              " ya da --install)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
