# PicoRV32 (RV32I) Assembler
## Sistem Programlama Dersi — 1. Proje

RV32I komut setinin **20 komutluk özenle seçilmiş alt kümesi** için
iki geçişli (two-pass) assembler implementasyonu.

---

## Proje Yapısı

```
assembler/
├── README.md            # Bu dosya
├── opcode_table.py      # OPTAB — 20 komutun encoding bilgileri
├── symbol_table.py      # SYMTAB — etiket-adres eşleme tablosu
├── register_table.py    # Register isim-numara tablosu (x0..x31, ABI)
├── parser.py            # Kaynak kod ayrıştırıcı
├── encoder.py           # 32-bit makine kodu üretici
├── assembler.py         # İki geçişli assembler (ana modül)
├── test1.bin            # Test 1 binary çıktı
└── test2.bin            # Test 2 binary çıktı
```

---

## Kurulum ve Çalıştırma

### Gereksinimler
- **Python 3.6+** (ek kütüphane gerekmez, standart kütüphane yeterli)

### Adım 1: Dosyaları bir klasöre koy
```bash
mkdir assembler
cd assembler
# Tüm .py dosyalarını bu klasöre kopyala
```

### Adım 2: Assembler'ı çalıştır (yerleşik testler ile)
```bash
python assembler.py
```
Bu komut iki test programını derleyip listing, sembol tablosu,
object program ve binary dosya üretir.

### Adım 3: Tek tek modülleri test et (opsiyonel)
```bash
python opcode_table.py     # OPTAB tablosunu yazdır
python register_table.py   # Register tablosunu yazdır
python parser.py           # Parser testlerini çalıştır
python encoder.py          # Encoder testlerini çalıştır (varsa)
```

### Adım 4: Kendi assembly dosyanı derle
```python
from assembler import Assembler

# Kaynak kodu satır listesi olarak ver
kaynak = [
    ".text",
    "_start: ADDI a0, zero, 42",
    "        ECALL",
]

asm = Assembler()
basarili = asm.assemble(kaynak, program_name="BENIM")
asm.print_listing()
asm.print_symbol_table()
asm.print_object_program()
asm.print_errors()
if basarili:
    asm.write_binary("cikti.bin")
```

---

## Desteklenen 20 Komut

| #  | Komut  | Format | Açıklama                       |
|----|--------|--------|--------------------------------|
| 1  | ADD    | R      | rd = rs1 + rs2                 |
| 2  | SUB    | R      | rd = rs1 - rs2                 |
| 3  | AND    | R      | rd = rs1 & rs2                 |
| 4  | OR     | R      | rd = rs1 \| rs2                |
| 5  | SLT    | R      | rd = (rs1 < rs2) ? 1 : 0      |
| 6  | ADDI   | I      | rd = rs1 + imm                 |
| 7  | ANDI   | I      | rd = rs1 & imm                 |
| 8  | SLLI   | I      | rd = rs1 << shamt              |
| 9  | SRLI   | I      | rd = rs1 >> shamt              |
| 10 | LW     | I      | rd = mem[rs1+imm]              |
| 11 | LB     | I      | rd = sign_ext(mem[rs1+imm][7:0])|
| 12 | JALR   | I      | rd = PC+4; PC = rs1+imm        |
| 13 | ECALL  | I      | Sistem çağrısı                 |
| 14 | SW     | S      | mem[rs1+imm] = rs2             |
| 15 | SB     | S      | mem[rs1+imm][7:0] = rs2[7:0]   |
| 16 | BEQ    | B      | if(rs1==rs2) PC += imm         |
| 17 | BNE    | B      | if(rs1!=rs2) PC += imm         |
| 18 | BLT    | B      | if(rs1<rs2) PC += imm          |
| 19 | LUI    | U      | rd = imm << 12                 |
| 20 | JAL    | J      | rd = PC+4; PC += imm           |

## Desteklenen Pseudo-Komutlar

| Pseudo | Dönüşüm             |
|--------|----------------------|
| NOP    | ADDI x0, x0, 0      |
| MV     | ADDI rd, rs, 0      |
| LI     | ADDI rd, x0, imm    |
| NEG    | SUB rd, x0, rs      |
| J      | JAL x0, offset       |
| JR     | JALR x0, rs, 0      |
| RET    | JALR x0, x1, 0      |
| CALL   | JAL x1, offset       |
| BEQZ   | BEQ rs, x0, offset  |
| BNEZ   | BNE rs, x0, offset  |

## Desteklenen Direktifler

`.text`, `.data`, `.word`, `.byte`, `.org`, `.end`, `.equ`, `.space`, `.string`
