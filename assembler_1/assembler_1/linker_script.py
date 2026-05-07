"""
PicoRV32 Linker Script - Basit KEY=VALUE Formati
=================================================
GNU ld'nin ld script sentaksi (cok daha karisik) yerine,
akademik proje icin yeterli olan minimal bir konfigurasyon
dosyasi formati. Yorumlar '#' ile baslar.

Ornek:
    # Tang Nano 9K + PicoRV32 BRAM init
    TEXT_ORIGIN = 0x00000000
    TEXT_LENGTH = 0x00010000
    DATA_ORIGIN = 0x00010000
    DATA_LENGTH = 0x00010000
    ENTRY       = _start

Tum alanlarin makul varsayilanlari vardir; sadece gerekenleri
override etmen yeterli.
"""

from dataclasses import dataclass


@dataclass
class LinkerScript:
    text_origin: int = 0x00000000
    text_length: int = 0x00010000
    data_origin: int = 0x00010000
    data_length: int = 0x00010000
    entry: str = "_start"

    @classmethod
    def parse(cls, text: str) -> "LinkerScript":
        ls = cls()
        for ln, raw in enumerate(text.splitlines(), 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if "=" not in line:
                raise ValueError(f"Linker script satir {ln}: '=' yok -> {raw!r}")
            key, val = line.split("=", 1)
            key = key.strip().upper()
            val = val.strip().strip('"').strip("'")
            if key == "TEXT_ORIGIN":   ls.text_origin = int(val, 0)
            elif key == "TEXT_LENGTH": ls.text_length = int(val, 0)
            elif key == "DATA_ORIGIN": ls.data_origin = int(val, 0)
            elif key == "DATA_LENGTH": ls.data_length = int(val, 0)
            elif key == "ENTRY":       ls.entry = val
            else:
                raise ValueError(f"Linker script satir {ln}: bilinmeyen anahtar {key!r}")
        return ls

    @classmethod
    def read(cls, path: str) -> "LinkerScript":
        with open(path, "r", encoding="utf-8") as f:
            return cls.parse(f.read())

    def __repr__(self):
        return (f"LinkerScript(text=0x{self.text_origin:08X}+{self.text_length}, "
                f"data=0x{self.data_origin:08X}+{self.data_length}, "
                f"entry={self.entry!r})")
