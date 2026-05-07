"""
PicoRV32 (RV32I) Linker - Iki Gecisli (Two-Pass) Bagleyici
===========================================================
Birden fazla .o.json nesne dosyasini birlestirip tek bir bellek
imaji uretir. Mantik klasik linker tasariminin minimal versiyonu:

    Pass 1 - Layout & Symbol Resolution:
        * Her dosyanin section'larini ardisik dizecek sekilde mutlak
          adres atar (text_origin'den baslayarak; .data ayri origin).
        * Her GLOBAL+defined sembol icin mutlak adres hesaplanir,
          global symbol table'a eklenir. Cift tanim varsa hata.
        * Her GLOBAL+undefined (extern) sembol global table'da
          aranir; yoksa "undefined reference" hatasi.
        * Entry sembolu cozulur.
        * Section verileri text_image / data_image bayt dizisine
          kopyalanir (henuz yamasiz; placeholder'lar imm=0).

    Pass 2 - Relocation:
        * Her objenin relocation tablosu islenir.
        * Sembolun mutlak adresi global table'dan alinir.
        * Tipe gore yer-baglantisi degeri hesaplanir (PC-relative
          ya da absolute), ilgili immediate alani komut icine
          yamanir (bit_layout helper'lari ile).

L-1 icin gereken cekirdek tipler: R_RISCV_JAL, R_RISCV_BRANCH.
HI20/LO12_I/LO12_S/PCREL_* iskeletleri var; L-2 sirasinda
gercek hesaplamalar tamamlanir.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from object_format import (
    ObjectFile, Symbol, Relocation,
    R_RISCV_BRANCH, R_RISCV_JAL,
    R_RISCV_HI20, R_RISCV_LO12_I, R_RISCV_LO12_S,
    R_RISCV_PCREL_HI20, R_RISCV_PCREL_LO12_I,
    SECTION_TEXT, SECTION_DATA, SECTION_ABS,
    BINDING_LOCAL, BINDING_GLOBAL,
)
from bit_layout import (
    pack_b_imm, pack_j_imm, pack_i_imm, pack_s_imm, pack_u_imm,
    B_IMM_MASK, J_IMM_MASK, I_IMM_MASK, S_IMM_MASK, U_IMM_MASK,
    read_word_le, write_word_le,
    fits_signed,
)
from linker_script import LinkerScript


def _align_up(n, alignment):
    return (n + alignment - 1) & ~(alignment - 1)


@dataclass
class GlobalSym:
    name: str
    abs_addr: int
    section: str
    file: str


@dataclass
class MapEntry:
    name: str
    abs_addr: int
    section: str
    binding: str
    file: str


class Linker:
    def __init__(self, script: Optional[LinkerScript] = None):
        self.script = script or LinkerScript()
        self._objects: List[Tuple[str, ObjectFile]] = []
        self._global_symbols: Dict[str, GlobalSym] = {}
        self._map_entries: List[MapEntry] = []
        self._section_bases: Dict[Tuple[int, str], int] = {}
        self._section_sizes: Dict[Tuple[int, str], int] = {}
        self._text_image = bytearray()
        self._data_image = bytearray()
        self._entry_address: Optional[int] = None
        self._errors: List[str] = []
        self._reloc_log: List[str] = []  # human-readable trace, raporda kullanilir

    # ── Public API ──

    def add_object(self, path: str):
        obj = ObjectFile.read(path)
        self._objects.append((path, obj))
        return obj

    def add_object_in_memory(self, name: str, obj: ObjectFile):
        """Test/automation amacli: dosyadan okumadan bir ObjectFile ekle."""
        self._objects.append((name, obj))

    def link(self) -> bool:
        if not self._objects:
            self._errors.append("Linklenecek nesne dosyasi yok")
            return False
        self._pass1_layout_and_resolve()
        if self._errors:
            return False
        self._pass2_relocate()
        return not self._errors

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    @property
    def text_image(self) -> bytes:
        return bytes(self._text_image)

    @property
    def data_image(self) -> bytes:
        return bytes(self._data_image)

    @property
    def entry_address(self) -> Optional[int]:
        return self._entry_address

    @property
    def map_entries(self) -> List[MapEntry]:
        return list(self._map_entries)

    @property
    def reloc_log(self) -> List[str]:
        return list(self._reloc_log)

    # ── Pass 1 ──

    def _pass1_layout_and_resolve(self):
        # 1) Section base address atamasi (text once, data sonra)
        text_cursor = 0
        data_cursor = 0
        for idx, (path, obj) in enumerate(self._objects):
            for sec_name in (SECTION_TEXT, SECTION_DATA):
                sec = obj.sections.get(sec_name)
                if sec is None or sec.size == 0:
                    continue
                if sec_name == SECTION_TEXT:
                    base = self.script.text_origin + text_cursor
                    text_cursor = _align_up(text_cursor + sec.size, 4)
                else:
                    base = self.script.data_origin + data_cursor
                    data_cursor = _align_up(data_cursor + sec.size, 4)
                self._section_bases[(idx, sec_name)] = base
                self._section_sizes[(idx, sec_name)] = sec.size

        # Boyut kapasite kontrolu
        if text_cursor > self.script.text_length:
            self._errors.append(
                f".text bolumu sigmadi: {text_cursor}B > script.text_length={self.script.text_length}B")
        if data_cursor > self.script.data_length:
            self._errors.append(
                f".data bolumu sigmadi: {data_cursor}B > script.data_length={self.script.data_length}B")

        # 2) Image tamponlarini ayir ve section verilerini yerlestir
        self._text_image = bytearray(text_cursor)
        self._data_image = bytearray(data_cursor)
        for idx, (path, obj) in enumerate(self._objects):
            for sec_name in (SECTION_TEXT, SECTION_DATA):
                sec = obj.sections.get(sec_name)
                if sec is None or sec.size == 0:
                    continue
                base = self._section_bases[(idx, sec_name)]
                if sec_name == SECTION_TEXT:
                    img_off = base - self.script.text_origin
                    self._text_image[img_off:img_off + sec.size] = sec.data
                else:
                    img_off = base - self.script.data_origin
                    self._data_image[img_off:img_off + sec.size] = sec.data

        # 3) Sembolleri global ve map'e dagit
        for idx, (path, obj) in enumerate(self._objects):
            for sym in obj.symbols:
                # Mutlak adres hesabi
                if sym.section == SECTION_ABS:
                    abs_addr = sym.offset
                elif sym.defined and sym.section in (SECTION_TEXT, SECTION_DATA):
                    base = self._section_bases.get((idx, sym.section))
                    if base is None:
                        # Bos section'a referans (anlamlandirilamaz)
                        continue
                    abs_addr = base + sym.offset
                else:
                    abs_addr = 0  # extern; gercek adres lookup zamani belli olur

                # Map kaydi
                if sym.defined:
                    self._map_entries.append(MapEntry(
                        name=sym.name, abs_addr=abs_addr,
                        section=sym.section or "?",
                        binding=sym.binding, file=path,
                    ))

                # Global tabloya ekleme (sadece GLOBAL + defined)
                if sym.binding == BINDING_GLOBAL and sym.defined:
                    if sym.name in self._global_symbols:
                        prev = self._global_symbols[sym.name]
                        self._errors.append(
                            f"Multiple definition of '{sym.name}': "
                            f"{prev.file} ve {path}")
                        continue
                    self._global_symbols[sym.name] = GlobalSym(
                        name=sym.name,
                        abs_addr=abs_addr,
                        section=sym.section,
                        file=path,
                    )

        # 4) Extern'lerin cozulebildigini dogrula
        for idx, (path, obj) in enumerate(self._objects):
            for sym in obj.externals():
                if sym.name not in self._global_symbols:
                    self._errors.append(
                        f"{path}: undefined reference to '{sym.name}'")

        # 5) Entry sembolunu coz
        if self.script.entry:
            ent = self._global_symbols.get(self.script.entry)
            if ent is None:
                self._errors.append(
                    f"Entry sembolu '{self.script.entry}' GLOBAL olarak tanimli degil")
            else:
                self._entry_address = ent.abs_addr

    # ── Pass 2 ──

    def _pass2_relocate(self):
        for idx, (path, obj) in enumerate(self._objects):
            for r in obj.relocations:
                self._apply_relocation(idx, path, r)

    def _apply_relocation(self, obj_idx, path, r: Relocation):
        if r.symbol not in self._global_symbols:
            # Pass 1'de yakalanmis olmali ama emin ol
            self._errors.append(f"{path}: relocation '{r.symbol}' icin sembol bulunamadi")
            return

        sym_addr = self._global_symbols[r.symbol].abs_addr
        section_base = self._section_bases.get((obj_idx, r.section))
        if section_base is None:
            self._errors.append(
                f"{path}: relocation bilinmeyen section '{r.section}' icin")
            return

        patch_abs = section_base + r.offset

        # Image ve image-icindeki offset
        if r.section == SECTION_TEXT:
            image = self._text_image
            origin = self.script.text_origin
        elif r.section == SECTION_DATA:
            image = self._data_image
            origin = self.script.data_origin
        else:
            self._errors.append(f"{path}: relocation desteklenmeyen section '{r.section}'")
            return

        img_off = patch_abs - origin
        old_code = read_word_le(image, img_off)

        new_code = self._compute_patched_word(
            old_code=old_code,
            patch_abs=patch_abs,
            sym_addr=sym_addr,
            reloc_type=r.type,
            addend=r.addend,
            path=path,
            symbol=r.symbol,
        )
        if new_code is None:
            return  # error already logged

        write_word_le(image, img_off, new_code)

        self._reloc_log.append(
            f"{path} {r.section}@0x{r.offset:04X} {r.type:<22} "
            f"sym='{r.symbol}' resolved=0x{sym_addr:08X} "
            f"patch_abs=0x{patch_abs:08X} old=0x{old_code:08X} new=0x{new_code:08X}"
        )

    def _compute_patched_word(self, *, old_code, patch_abs, sym_addr,
                              reloc_type, addend, path, symbol):
        if reloc_type == R_RISCV_JAL:
            disp = sym_addr + addend - patch_abs
            if not fits_signed(disp, 21):
                self._errors.append(
                    f"{path}: '{symbol}' icin JAL displacement {disp} 21-bit aralik disinda")
                return None
            if disp & 0x1:
                self._errors.append(
                    f"{path}: '{symbol}' JAL displacement {disp} 2-byte hizali degil")
                return None
            return (old_code & ~J_IMM_MASK) | pack_j_imm(disp)

        if reloc_type == R_RISCV_BRANCH:
            disp = sym_addr + addend - patch_abs
            if not fits_signed(disp, 13):
                self._errors.append(
                    f"{path}: '{symbol}' icin BRANCH displacement {disp} 13-bit aralik disinda")
                return None
            if disp & 0x1:
                self._errors.append(
                    f"{path}: '{symbol}' BRANCH displacement {disp} 2-byte hizali degil")
                return None
            return (old_code & ~B_IMM_MASK) | pack_b_imm(disp)

        if reloc_type == R_RISCV_HI20:
            # LUI rd, %hi(symbol). Asagi 12 bit'i de ADDI/LW gibi LO12 ile alinir;
            # ancak LUI %hi sadece ust 20 bit'i tasir, asagi 12 bit isaret-genisletme
            # nedeniyle dengelenmelidir: hi = (sym + 0x800) >> 12
            value = (sym_addr + addend + 0x800) & 0xFFFFFFFF
            hi = (value >> 12) & 0xFFFFF
            return (old_code & ~U_IMM_MASK) | pack_u_imm(hi)

        if reloc_type == R_RISCV_LO12_I:
            value = sym_addr + addend
            lo = value & 0xFFF  # signed 12-bit alt
            return (old_code & ~I_IMM_MASK) | pack_i_imm(lo)

        if reloc_type == R_RISCV_LO12_S:
            value = sym_addr + addend
            lo = value & 0xFFF
            return (old_code & ~S_IMM_MASK) | pack_s_imm(lo)

        if reloc_type == R_RISCV_PCREL_HI20:
            disp = (sym_addr + addend - patch_abs) & 0xFFFFFFFF
            value = (disp + 0x800) & 0xFFFFFFFF
            hi = (value >> 12) & 0xFFFFF
            return (old_code & ~U_IMM_MASK) | pack_u_imm(hi)

        if reloc_type == R_RISCV_PCREL_LO12_I:
            # NOT: GNU as semantigi cifti soyle uretir: HI20 paired with addend
            # noktasini gosteren bir etiket. Burada basitlestiriyoruz: addend,
            # AUIPC komutunun bulundugu adrese ait offset kabul edilir.
            # L-2'de pratik testle netlestireceğiz.
            disp = sym_addr + addend - patch_abs
            lo = disp & 0xFFF
            return (old_code & ~I_IMM_MASK) | pack_i_imm(lo)

        self._errors.append(f"{path}: desteklenmeyen relocation tipi {reloc_type}")
        return None

    # ── Map / Diagnostic Ciktisi ──

    def print_map(self):
        print()
        print(f"  {'='*72}")
        print(f"  LINK MAP")
        print(f"  {'='*72}")
        print(f"  Script: {self.script}")

        print(f"\n  Section Bases:")
        for (idx, sec), base in sorted(self._section_bases.items()):
            path = self._objects[idx][0]
            sz = self._section_sizes[(idx, sec)]
            print(f"    {sec:<8} 0x{base:08X} - 0x{base+sz:08X}  ({sz:>4}B)  {path}")

        print(f"\n  Symbols (defined):")
        for m in sorted(self._map_entries, key=lambda e: (e.abs_addr, e.name)):
            print(f"    {m.name:<16} 0x{m.abs_addr:08X}  {m.binding:<7} "
                  f"{m.section:<8}  {m.file}")

        if self.script.entry:
            ent_addr = self._entry_address if self._entry_address is not None else 0
            print(f"\n  Entry: {self.script.entry} @ 0x{ent_addr:08X}")

        if self._reloc_log:
            print(f"\n  Relocations applied ({len(self._reloc_log)}):")
            for line in self._reloc_log:
                print(f"    {line}")

        if self._errors:
            print(f"\n  ERRORS ({len(self._errors)}):")
            for e in self._errors:
                print(f"    !! {e}")

        print(f"\n  text_image: {len(self._text_image)} bytes @ 0x{self.script.text_origin:08X}")
        print(f"  data_image: {len(self._data_image)} bytes @ 0x{self.script.data_origin:08X}")
        print(f"  {'='*72}")

    def write_text_binary(self, path):
        with open(path, "wb") as f:
            f.write(self._text_image)
        return path

    def write_data_binary(self, path):
        with open(path, "wb") as f:
            f.write(self._data_image)
        return path
