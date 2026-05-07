"""
PicoRV32 Toolchain Driver - Komut Satiri
=========================================
Tek komutla zinciri kosturur:
    1. Her .s/.asm kaynak dosyayi assemble eder -> .o.json
    2. Tum .o.json'lari verilen linker script ile birlestirir
    3. Flat binary (.bin) ve Verilog hex (.hex) cikti uretir
    4. Linker map'ini .map.txt olarak yazar (rapor icin)

Kullanim:
    python run_link.py [-T script.ld] [-o out_base] [-v] kaynak1 kaynak2 ...

Ornekler:
    python run_link.py tests/link/L1_basic_jal/main.s \
                       tests/link/L1_basic_jal/func.s \
                       -T tests/link/L1_basic_jal/linker.ld \
                       -o build/l1
    python run_link.py main.o.json delay.o.json -o build/firmware
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assembler import assemble_file
from linker import Linker
from linker_script import LinkerScript
from hex_emitter import write_raw_bin, write_verilog_hex


def main():
    p = argparse.ArgumentParser(description="PicoRV32 assembler+linker driver")
    p.add_argument("sources", nargs="+",
                   help="Kaynak: .s / .asm (assemble edilir) ya da .o.json (dogrudan linklenir)")
    p.add_argument("-T", "--script", default=None,
                   help="Linker script dosyasi (default: yerleşik varsayilanlar)")
    p.add_argument("-o", "--output", default=None,
                   help="Cikti taban adi (default: ilk kaynagin basename'i)")
    p.add_argument("--no-bin", action="store_true", help=".bin cikarma")
    p.add_argument("--no-hex", action="store_true", help=".hex cikarma")
    p.add_argument("--word-size", type=int, default=4, help="Verilog hex word size (1/2/4)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    # Linker script
    if args.script:
        try:
            script = LinkerScript.read(args.script)
        except Exception as e:
            print(f"HATA: linker script okunamadi: {e}", file=sys.stderr)
            return 2
    else:
        script = LinkerScript()
    if args.verbose:
        print(f"  [Script] {script}")

    # Output base
    out_base = args.output
    if out_base is None:
        first = args.sources[0]
        out_base = os.path.splitext(os.path.basename(first))[0]
        out_dir  = os.path.dirname(os.path.abspath(first)) or "."
        out_base = os.path.join(out_dir, out_base)
    out_dir = os.path.dirname(out_base) or "."
    os.makedirs(out_dir, exist_ok=True)

    # Kaynaklari isle: .s/.asm -> assemble; .o.json -> dogrudan
    obj_paths = []
    for src in args.sources:
        if not os.path.isfile(src):
            print(f"HATA: '{src}' bulunamadi", file=sys.stderr)
            return 2
        ext = os.path.splitext(src)[1].lower()
        if ext in (".s", ".asm"):
            if args.verbose:
                print(f"  [Assemble] {src}")
            asm, ok = assemble_file(src)
            if not ok:
                print(f"HATA: '{src}' assembly basarisiz:", file=sys.stderr)
                for e in asm._errors:
                    print(f"  {e}", file=sys.stderr)
                return 1
            o_path = os.path.splitext(src)[0] + ".o.json"
            asm.to_object_file(source_name=os.path.basename(src)).write(o_path)
            obj_paths.append(o_path)
            if args.verbose:
                print(f"             -> {o_path}")
        elif ext == ".json":
            obj_paths.append(src)
        else:
            print(f"HATA: bilinmeyen uzanti: {src}", file=sys.stderr)
            return 2

    # Link
    if args.verbose:
        print(f"  [Link] {len(obj_paths)} obje")
    ld = Linker(script)
    for p_ in obj_paths:
        ld.add_object(p_)
    ok = ld.link()
    if not ok:
        print("LINK HATALI:", file=sys.stderr)
        for e in ld.errors:
            print(f"  {e}", file=sys.stderr)
        # map hatali olsa da yazilsin (debug icin)
        _write_map(ld, out_base + ".map.txt")
        return 1

    # Cikti
    if not args.no_bin:
        bin_path = out_base + ".bin"
        write_raw_bin(ld.text_image, bin_path)
        print(f"  [BIN] {bin_path} ({len(ld.text_image)}B)")

    if not args.no_hex:
        hex_path = out_base + ".hex"
        write_verilog_hex(ld.text_image, hex_path, word_size=args.word_size)
        print(f"  [HEX] {hex_path}")

    map_path = out_base + ".map.txt"
    _write_map(ld, map_path)
    print(f"  [MAP] {map_path}")

    print(f"  Entry: 0x{ld.entry_address:08X}" if ld.entry_address is not None else "  Entry: yok")
    return 0


def _write_map(ld: Linker, path: str):
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ld.print_map()
    with open(path, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())


if __name__ == "__main__":
    raise SystemExit(main())
