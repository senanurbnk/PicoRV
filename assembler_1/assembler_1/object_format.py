"""
PicoRV32 (RV32I) Linker - Object Dosya Formati (.o.json)
=========================================================
Assembler'in urettigi yapili nesne dosyasi formati.
Linker bu dosyalari okur, sembol cozumler, relocation uygular,
flat binary (.bin) ve Verilog hex (.hex) cikartir.

Sema (JSON):
    {
      "magic":   "PICORV-OBJ",
      "version": 1,
      "source":  "main.s",
      "sections": {
        ".text": { "size": <int>, "data": "<hex bytes LE>" },
        ".data": { "size": <int>, "data": "<hex bytes>"   }   # opsiyonel
      },
      "symbols": [
        { "name": str, "section": ".text"|".data"|".abs"|null,
          "offset": int, "binding": "LOCAL"|"GLOBAL", "defined": bool }
      ],
      "relocations": [
        { "section": ".text"|".data", "offset": int,
          "type": "R_RISCV_JAL"|...,
          "symbol": str, "addend": int }
      ]
    }

Sembol section degerleri:
    ".text" / ".data" : Bu dosyanin ilgili section'inda tanimli
    ".abs"            : .equ ile tanimli mutlak sabit (yer baglantisiz)
    null              : Tanimsiz / harici (binding=GLOBAL + defined=False)
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


MAGIC = "PICORV-OBJ"
VERSION = 1

# Binding
BINDING_LOCAL = "LOCAL"
BINDING_GLOBAL = "GLOBAL"

# Ozel section adlari
SECTION_TEXT = ".text"
SECTION_DATA = ".data"
SECTION_ABS = ".abs"

# Relocation tipleri (RISC-V psABI alt kumesi)
R_RISCV_BRANCH      = "R_RISCV_BRANCH"        # B-format, 13-bit PC-rel
R_RISCV_JAL         = "R_RISCV_JAL"           # J-format, 21-bit PC-rel
R_RISCV_HI20        = "R_RISCV_HI20"          # LUI: target[31:12] absolute
R_RISCV_LO12_I      = "R_RISCV_LO12_I"        # ADDI/LW vb: target[11:0]
R_RISCV_LO12_S      = "R_RISCV_LO12_S"        # SW/SB:      target[11:0] (S-format)
R_RISCV_PCREL_HI20  = "R_RISCV_PCREL_HI20"    # AUIPC: (target-PC)[31:12]
R_RISCV_PCREL_LO12_I = "R_RISCV_PCREL_LO12_I" # PC-relative LO12, I-format

ALL_RELOC_TYPES = {
    R_RISCV_BRANCH, R_RISCV_JAL, R_RISCV_HI20,
    R_RISCV_LO12_I, R_RISCV_LO12_S,
    R_RISCV_PCREL_HI20, R_RISCV_PCREL_LO12_I,
}


@dataclass
class Symbol:
    name: str
    section: Optional[str]    # ".text", ".data", "ABS", or None
    offset: int
    binding: str              # "LOCAL" / "GLOBAL"
    defined: bool

    def is_external(self) -> bool:
        return self.binding == BINDING_GLOBAL and not self.defined


@dataclass
class Relocation:
    section: str              # ".text" / ".data"
    offset: int               # Section icinde patch yapilacak byte offset
    type: str                 # ALL_RELOC_TYPES'tan biri
    symbol: str
    addend: int = 0


@dataclass
class Section:
    name: str
    size: int
    data: bytes = b""

    def __post_init__(self):
        if isinstance(self.data, str):
            self.data = _hex_to_bytes(self.data)
        if self.size == 0 and self.data:
            self.size = len(self.data)


@dataclass
class ObjectFile:
    source: str = ""
    sections: Dict[str, Section] = field(default_factory=dict)
    symbols: List[Symbol] = field(default_factory=list)
    relocations: List[Relocation] = field(default_factory=list)
    magic: str = MAGIC
    version: int = VERSION

    # --- Section yardimcilar ---
    def get_section(self, name: str) -> Optional[Section]:
        return self.sections.get(name)

    def ensure_section(self, name: str) -> Section:
        if name not in self.sections:
            self.sections[name] = Section(name=name, size=0, data=b"")
        return self.sections[name]

    # --- Symbol yardimcilar ---
    def find_symbol(self, name: str) -> Optional[Symbol]:
        for s in self.symbols:
            if s.name == name:
                return s
        return None

    def globals(self) -> List[Symbol]:
        return [s for s in self.symbols if s.binding == BINDING_GLOBAL and s.defined]

    def externals(self) -> List[Symbol]:
        return [s for s in self.symbols if s.is_external()]

    # --- JSON I/O ---
    def to_json(self, indent: int = 2) -> str:
        d = {
            "magic": self.magic,
            "version": self.version,
            "source": self.source,
            "sections": {
                name: {"size": sec.size, "data": _bytes_to_hex(sec.data)}
                for name, sec in self.sections.items()
            },
            "symbols": [asdict(s) for s in self.symbols],
            "relocations": [asdict(r) for r in self.relocations],
        }
        return json.dumps(d, indent=indent)

    @classmethod
    def from_json(cls, s: str) -> "ObjectFile":
        d = json.loads(s)
        if d.get("magic") != MAGIC:
            raise ValueError(f"Gecersiz magic: {d.get('magic')!r} (beklenen {MAGIC!r})")
        if d.get("version") != VERSION:
            raise ValueError(f"Desteklenmeyen surum: {d.get('version')} (beklenen {VERSION})")

        sections = {}
        for name, sec in d.get("sections", {}).items():
            sections[name] = Section(
                name=name,
                size=int(sec.get("size", 0)),
                data=_hex_to_bytes(sec.get("data", "")),
            )

        symbols = [Symbol(**sd) for sd in d.get("symbols", [])]

        relocs = []
        for rd in d.get("relocations", []):
            t = rd.get("type")
            if t not in ALL_RELOC_TYPES:
                raise ValueError(f"Bilinmeyen relocation tipi: {t!r}")
            relocs.append(Relocation(
                section=rd["section"],
                offset=int(rd["offset"]),
                type=t,
                symbol=rd["symbol"],
                addend=int(rd.get("addend", 0)),
            ))

        return cls(
            source=d.get("source", ""),
            sections=sections,
            symbols=symbols,
            relocations=relocs,
        )

    def write(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
            f.write("\n")

    @classmethod
    def read(cls, path: str) -> "ObjectFile":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())


def _bytes_to_hex(data: bytes) -> str:
    if not data:
        return ""
    return " ".join(f"{b:02X}" for b in data)


def _hex_to_bytes(s: str) -> bytes:
    s = (s or "").strip()
    if not s:
        return b""
    return bytes(int(tok, 16) for tok in s.split())
