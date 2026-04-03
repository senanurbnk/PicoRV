"""
PicoRV32 (RV32I) Assembler — Çalıştırıcı
==========================================
Kullanım:
    python run.py dosya1.asm dosya2.asm ...
    python run.py             (argüman verilmezse test1.asm ve test2.asm kullanılır)

Her .asm dosyası için üretilen çıktılar:
    <isim>.bin   — binary makine kodu (little-endian, doğrudan PicoRV32'ye yüklenebilir)
    <isim>.txt   — okunabilir rapor: listing + sembol tablosu + object program + hex dump
"""

import sys
import os

# assembler.py ile aynı dizinde çalışabilmek için path ayarı
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assembler import assemble_and_save


def main():
    # Komut satırı argümanları verilmişse onları kullan,
    # verilmemişse varsayılan test dosyalarını kullan.
    if len(sys.argv) > 1:
        asm_files = sys.argv[1:]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        asm_files  = [
            os.path.join(script_dir, "test1.asm"),
            os.path.join(script_dir, "test2.asm"),
        ]

    print("=" * 70)
    print("  PicoRV32 (RV32I) ASSEMBLER — Çalıştırıcı")
    print("=" * 70)

    results = []

    for asm_path in asm_files:
        print(f"\n{'─'*70}")
        print(f"  Kaynak: {asm_path}")
        print(f"{'─'*70}\n")

        try:
            success, bin_path, txt_path = assemble_and_save(
                asm_path  = asm_path,
                out_dir   = None,     # None → kaynak dosyayla aynı dizin
                write_bin = True,
                write_txt = True,
                verbose   = True,
            )
            results.append((asm_path, success, bin_path, txt_path))

        except FileNotFoundError as e:
            print(f"  HATA: {e}")
            results.append((asm_path, False, None, None))
        except Exception as e:
            print(f"  BEKLENMEDİK HATA: {e}")
            results.append((asm_path, False, None, None))

    # Özet
    print(f"\n{'='*70}")
    print(f"  ÖZET")
    print(f"{'='*70}")
    for asm_path, success, bin_path, txt_path in results:
        durum = "BAŞARILI ✓" if success else "BAŞARISIZ ✗"
        print(f"  {os.path.basename(asm_path):<20} {durum}")
        if bin_path and success:
            size = os.path.getsize(bin_path)
            print(f"    ├─ BIN: {bin_path}  ({size} byte)")
        if txt_path:
            print(f"    └─ TXT: {txt_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()