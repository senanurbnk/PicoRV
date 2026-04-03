"""
PicoRV32 (RV32I) Assembler - Symbol Table Modülü
=================================================
Kaynak programdaki etiketlerin adreslerini tutan dinamik hash tablosu.

Pass 1'de doldurulur: etiket + LOCCTR adresi
Pass 2'de okunur:     operandlardaki sembollerin adresi bulunur

Özellikler:
    - Çift tanımlı sembol kontrolü
    - Forward reference desteği
    - Tanımsız sembol tespiti
"""


class SymbolEntry:
    def __init__(self, name, address=0, defined=True, section=".text", line_num=0):
        self.name = name
        self.address = address
        self.defined = defined
        self.section = section
        self.line_num = line_num
        self.error = None

    def __repr__(self):
        status = "TANIMLI" if self.defined else "TANIMSIZ"
        return f"'{self.name}' addr=0x{self.address:08X} {status} ({self.section})"


class SymbolTable:
    def __init__(self):
        self._table = {}

    def add(self, name, address, section=".text", line_num=0):
        key = name.upper()
        if key in self._table:
            existing = self._table[key]
            if existing.defined:
                existing.error = f"Çift tanımlı sembol: '{name}' (ilk: satır {existing.line_num})"
                return False
        self._table[key] = SymbolEntry(name, address, True, section, line_num)
        return True

    def add_forward_reference(self, name, line_num=0):
        key = name.upper()
        if key not in self._table:
            self._table[key] = SymbolEntry(name, 0, False, line_num=line_num)

    def lookup(self, name):
        return self._table.get(name.upper(), None)

    def contains(self, name):
        return name.upper() in self._table

    def get_address(self, name):
        entry = self.lookup(name)
        if entry and entry.defined:
            return entry.address
        return None

    def get_undefined_symbols(self):
        return [e for e in self._table.values() if not e.defined]

    def get_errors(self):
        return [e for e in self._table.values() if e.error is not None]

    def size(self):
        return len(self._table)

    def clear(self):
        self._table.clear()

    def print_table(self):
        print("\n\n")
        print(f"{'SYMBOL TABLE (SYMTAB)':^72}")
        print(f"  {'Sembol':<16} {'Adres':>12} {'Bölüm':<8} {'Satır':>5}  {'Durum'}")
        print(f"  {'-'*66}")
        for key in sorted(self._table.keys()):
            e = self._table[key]
            status = "TANIMLI" if e.defined else "TANIMSIZ"
            if e.error:
                status += f" HATA: {e.error}"
            print(f"  {e.name:<16} 0x{e.address:08X}  {e.section:<8} {e.line_num:>5}  {status}")
        print(f"  {'-'*66}")
        print(f"  Toplam: {self.size()} sembol")
        print("\n\n")
        undef = self.get_undefined_symbols()
        if undef:
            print(f"  UYARI: {len(undef)} tanımsız sembol!")
