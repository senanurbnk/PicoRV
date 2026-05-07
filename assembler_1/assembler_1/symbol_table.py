"""
PicoRV32 (RV32I) Assembler - Symbol Table Modulu
=================================================
Kaynak programdaki etiketlerin adreslerini tutan dinamik hash tablosu.

Pass 1'de doldurulur: etiket + LOCCTR adresi
Pass 2'de okunur:     operandlardaki sembollerin adresi bulunur

Ozellikler:
    - Cift tanimli sembol kontrolu
    - Forward reference destegi
    - Tanimsiz sembol tespiti
    - Binding (LOCAL / GLOBAL) destegi  --> linker icin
"""


# Binding sabitleri object_format ile birebir ayni string degerleri.
# Dogrudan oraya bagimli olmamak icin burada da tanimli; sema versiyonuyla
# birlikte degisirse iki yerden de guncellenmeli.
BINDING_LOCAL = "LOCAL"
BINDING_GLOBAL = "GLOBAL"


class SymbolEntry:
    def __init__(self, name, address=0, defined=True, section=".text",
                 line_num=0, binding=BINDING_LOCAL):
        self.name = name
        self.address = address
        self.defined = defined
        self.section = section          # ".text" / ".data" / ".abs" / None
        self.line_num = line_num
        self.binding = binding          # "LOCAL" / "GLOBAL"
        self.error = None

    def is_external(self):
        return self.binding == BINDING_GLOBAL and not self.defined

    def __repr__(self):
        status = "TANIMLI" if self.defined else "TANIMSIZ"
        sec = self.section if self.section else "UNDEF"
        return f"'{self.name}' addr=0x{self.address:08X} {status} ({sec},{self.binding})"


class SymbolTable:
    def __init__(self):
        self._table = {}

    def add(self, name, address, section=".text", line_num=0):
        key = name.upper()
        if key in self._table:
            existing = self._table[key]
            if existing.defined:
                existing.error = f"Cift tanimli sembol: '{name}' (ilk: satir {existing.line_num})"
                return False
            # Forward-ref ya da .global ile onceden ilan edilmis sembolu tanimli yap
            existing.address = address
            existing.section = section
            existing.line_num = line_num
            existing.defined = True
            return True
        self._table[key] = SymbolEntry(name, address, True, section, line_num)
        return True

    def add_forward_reference(self, name, line_num=0):
        key = name.upper()
        if key not in self._table:
            self._table[key] = SymbolEntry(name, 0, False, section=None, line_num=line_num)

    def mark_global(self, name, line_num=0):
        """`.global name` direktifi gorulunce cagrilir.
        Sembol tabloda yoksa undefined-extern olarak on kayit olusturur;
        varsa binding'ini GLOBAL'e yukseltir (digerleri korunur)."""
        key = name.upper()
        if key in self._table:
            self._table[key].binding = BINDING_GLOBAL
        else:
            e = SymbolEntry(name, 0, defined=False, section=None,
                            line_num=line_num, binding=BINDING_GLOBAL)
            self._table[key] = e

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
        # Linker'in cozecegi extern'ler hata sayilmaz; sadece LOCAL+undefined hata.
        return [e for e in self._table.values()
                if not e.defined and e.binding == BINDING_LOCAL]

    def get_globals(self):
        return [e for e in self._table.values()
                if e.binding == BINDING_GLOBAL and e.defined]

    def get_externals(self):
        return [e for e in self._table.values() if e.is_external()]

    def get_errors(self):
        return [e for e in self._table.values() if e.error is not None]

    def all_entries(self):
        return list(self._table.values())

    def size(self):
        return len(self._table)

    def clear(self):
        self._table.clear()

    def print_table(self):
        print("\n\n")
        print(f"{'SYMBOL TABLE (SYMTAB)':^72}")
        print(f"  {'Sembol':<16} {'Adres':>12} {'Bolum':<8} {'Bind':<7} {'Satir':>5}  {'Durum'}")
        print(f"  {'-'*72}")
        for key in sorted(self._table.keys()):
            e = self._table[key]
            status = "TANIMLI" if e.defined else ("EXTERN" if e.binding == BINDING_GLOBAL else "TANIMSIZ")
            sec = e.section if e.section else "UNDEF"
            if e.error:
                status += f" HATA: {e.error}"
            print(f"  {e.name:<16} 0x{e.address:08X}  {sec:<8} {e.binding:<7} {e.line_num:>5}  {status}")
        print(f"  {'-'*72}")
        print(f"  Toplam: {self.size()} sembol "
              f"(GLOBAL tanimli: {len(self.get_globals())}, "
              f"EXTERN: {len(self.get_externals())})")
        print("\n\n")
        undef = self.get_undefined_symbols()
        if undef:
            print(f"  UYARI: {len(undef)} cozulemeyen LOCAL sembol!")
