# PicoRV — RV32I Assembler + Linker + Tang Nano 9K SoC

**Sistem Programlama Dersi — Birleşik Proje (1 + 2 + 4)**

Bu repo, bir RV32I alt kümesi için yazılmış iki geçişli (two-pass) assembler'ın
**komple bir toolchain ve donanım yığınına** evrildiği bir akademik projedir.
Elde ettiğimiz son durum:

* `.s` (RISC-V assembly) → **assembler** → `.o.json` nesne dosyaları
* `.o.json` × N → **linker** → `.bin` + `.hex` + `_init.vh` + `.map.txt`
* `_init.vh` → **Verilog SoC** (PicoRV32 + BRAM + GPIO) → **Gowin sentez** → bitstream
* Bitstream → **Tang Nano 9K** → **6 LED'in fiziksel olarak sayması**

Yani yazdığımız Python toolchain'in ürettiği makine kodu, kendi yazdığımız bir
SoC içinde kendi yazdığımız bir bellek haritası üzerinden gerçek bir FPGA üstünde
gerçek LED'leri kontrol ediyor. **Cross-file relocation'larımız fiziksel bir
sistemde çalışıyor.**

---

## İçindekiler

1. [Genel Mimari](#genel-mimari)
2. [Klasör Yapısı](#klasör-yapısı)
3. [Faz 1 — Assembler (1. Proje)](#faz-1--assembler-1-proje)
4. [Faz 2 — Linker Pipeline (2. Proje)](#faz-2--linker-pipeline-2-proje)
5. [Faz 3 — Test Matrisi ve CLI](#faz-3--test-matrisi-ve-cli)
6. [Faz 4 — Tang Nano 9K SoC (FPGA Faz)](#faz-4--tang-nano-9k-soc-fpga-faz)
7. [Toolchain Komut Satırı Kullanımı](#toolchain-komut-satırı-kullanımı)
8. [SoC Mimarisi ve Bellek Haritası](#soc-mimarisi-ve-bellek-haritası)
9. [Gowin Build Adımları](#gowin-build-adımları)
10. [Debug Yolculuğu (Karşılaştığımız Sorunlar)](#debug-yolculuğu-karşılaştığımız-sorunlar)
11. [Doğrulama Metodolojisi](#doğrulama-metodolojisi)
12. [Lisanslar ve Atıflar](#lisanslar-ve-atıflar)
13. [Gelecek İşler](#gelecek-işler)

---

## Genel Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                         YAZILIM (Python)                         │
├─────────────────────────────────────────────────────────────────┤
│   .s / .asm                                                      │
│      ↓                                                           │
│   parser.py     →  ParsedLine + ParsedOperand                   │
│   opcode_table  →  OPTAB (20 RV32I komutu + 10 pseudo)          │
│   register_table→  RegisterTable (xN + ABI isimler)             │
│   symbol_table  →  SYMTAB (LOCAL/GLOBAL, defined/extern)        │
│      ↓                                                           │
│   encoder.py + bit_layout.py    → 32-bit makine kodu            │
│      ↓                                                           │
│   assembler.py (two-pass)       → Section + Symbol + Relocation │
│      ↓                                                           │
│   object_format.py              → .o.json (PICORV-OBJ v1)       │
│      ↓                                                           │
│   linker.py + linker_script.py  → flat memory image             │
│      ↓                                                           │
│   hex_emitter.py                → .bin / .hex / _init.vh        │
│                                                                  │
│   run_link.py = tek satır CLI driver, yukarıdaki zinciri çağırır │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DONANIM (Verilog + Gowin)                     │
├─────────────────────────────────────────────────────────────────┤
│   blink_init.vh  → bram.v `include                              │
│   picorv32.v     → CPU çekirdeği (Cliff Wolf, ISC)              │
│   bram.v         → 8 KB Block RAM (init: include)               │
│   gpio.v         → 6-bit LED MMIO @ 0x10000000                  │
│   soc_top.v      → bus + adres decode + reset + clock           │
│   tangnano9k.cst → pin atamaları (GW1NR-9 QFN88)                │
│   tangnano9k.sdc → 27 MHz timing constraint                     │
│      ↓                                                           │
│   Gowin EDA: GowinSynthesis + Place & Route                     │
│      ↓                                                           │
│   blink_soc.fs (bitstream)                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                  Tang Nano 9K (Sipeed, GW1NR-LV9QN88PC6)
                              ↓
                      LED1..LED6 binary olarak sayar
```

---

## Klasör Yapısı

```
PicoRV/
├── README.md                                  ← bu dosya
├── .gitignore
└── assembler_1/assembler_1/
    │
    ├── ─── Toolchain (Python) ───
    ├── opcode_table.py        # OPTAB — 20 komut + 10 pseudo
    ├── register_table.py      # xN ↔ ABI isim eşlemesi
    ├── symbol_table.py        # SYMTAB — LOCAL/GLOBAL, defined/extern
    ├── parser.py              # Kaynak ayrıştırıcı (label, mnem, operand, mem)
    ├── encoder.py             # 6 format encoder
    ├── bit_layout.py          # B/J/I/S/U immediate paketleyiciler (DRY)
    ├── assembler.py           # Two-pass assembler — relocation üretimi dahil
    ├── object_format.py       # .o.json sema + I/O
    ├── linker_script.py       # KEY=VALUE format linker config
    ├── linker.py              # Two-pass linker — pass 1 layout, pass 2 reloc
    ├── hex_emitter.py         # .bin / .hex / _init.vh / Intel HEX
    ├── run_link.py            # CLI driver: assemble → link → emit
    ├── gui.py                 # Opsiyonel Tkinter GUI (eski faz)
    ├── run.py                 # İlk faz CLI (legacy)
    │
    ├── ─── Test (regresyon) ───
    └── tests/link/
        ├── L1_basic_jal/      # Cross-file R_RISCV_JAL (main → func)
        │   ├── main.s, func.s, linker.ld
        │   ├── EXPECTED_*.o.json, EXPECTED_link.txt
        │   └── *.o.json (her run sonrası yeniden üretilir)
        └── L3_cross_branch/   # Cross-file R_RISCV_BRANCH (BEQZ pong)
            ├── ping.s, pong.s, linker.ld
            └── EXPECTED_link.txt
    │
    ├── ─── Firmware (asıl uygulama) ───
    └── firmware/blink/
        ├── main.s             # LED counter ana kod (cross-file CALL)
        ├── delay.s            # Busy-wait gecikme döngüsü
        ├── tangnano9k.ld      # Linker script (TEXT_ORIGIN=0x0)
        └── build/             # Toolchain çıktıları
            ├── blink.bin      # Raw flat binary (40 byte)
            ├── blink.hex      # Verilog $readmemh formatı
            ├── blink_init.vh  # Verilog `include header (toolchain → SoC köprüsü)
            ├── blink.map.txt  # Linker map (sembol adresleri, relocation log)
            ├── main.o.json    # Ara nesne dosyaları
            └── delay.o.json
    │
    ├── ─── Donanım (Verilog) ───
    ├── fpga/tangnano9k_soc/
    │   ├── soc_top.v          # Top module: clock, reset, bus, decode
    │   ├── bram.v             # 8 KB BRAM (include + $readmemh yedek)
    │   ├── gpio.v             # 6-bit LED MMIO
    │   ├── tangnano9k.cst     # Gowin pin constraints
    │   ├── tangnano9k.sdc     # Timing constraint (27 MHz)
    │   ├── blink.hex          # Buraya kopyalanır (Gowin'in görmesi için)
    │   ├── blink_init.vh      # bram.v'nin include ettiği init data
    │   ├── README.md          # Gowin GUI build adımları
    │   └── fpga_project/      # Gowin EDA proje klasörü (kullanıcının makinesinde)
    │       ├── *.gprj
    │       └── src/, impl/, ...
    │
    └── ─── Vendor ───
    └── vendor/picorv32/
        ├── picorv32.v         # Cliff Wolf (3049 satır, ISC lisansı)
        └── COPYING            # ISC license metni
```

---

## Faz 1 — Assembler (1. Proje)

### Amaç

RV32I komut setinin **20 komutluk özenle seçilmiş bir alt kümesi** için iki
geçişli (two-pass) bir assembler. Çıktı: SIC/XE benzeri Header–Text–End nesne
formatı + flat binary.

### Desteklenen 20 RV32I Komutu

| #  | Mnemonic | Format | Encoding (opcode/funct3/funct7) | Anlam |
|----|----------|--------|---------------------------------|-------|
| 1  | ADD      | R      | 0110011 / 000 / 0000000         | rd = rs1 + rs2 |
| 2  | SUB      | R      | 0110011 / 000 / 0100000         | rd = rs1 - rs2 |
| 3  | AND      | R      | 0110011 / 111 / 0000000         | rd = rs1 & rs2 |
| 4  | OR       | R      | 0110011 / 110 / 0000000         | rd = rs1 \| rs2 |
| 5  | SLT      | R      | 0110011 / 010 / 0000000         | rd = (rs1<rs2)?1:0 (signed) |
| 6  | ADDI     | I      | 0010011 / 000                   | rd = rs1 + imm |
| 7  | ANDI     | I      | 0010011 / 111                   | rd = rs1 & imm |
| 8  | SLLI     | I      | 0010011 / 001 / 0000000         | rd = rs1 << shamt |
| 9  | SRLI     | I      | 0010011 / 101 / 0000000         | rd = rs1 >> shamt (logical) |
| 10 | LW       | I      | 0000011 / 010                   | rd = mem[rs1+imm][31:0] |
| 11 | LB       | I      | 0000011 / 000                   | rd = sign_ext(mem[rs1+imm][7:0]) |
| 12 | JALR     | I      | 1100111 / 000                   | rd = PC+4; PC = (rs1+imm) & ~1 |
| 13 | ECALL    | I      | 1110011 / 000                   | Sistem çağrısı |
| 14 | SW       | S      | 0100011 / 010                   | mem[rs1+imm][31:0] = rs2 |
| 15 | SB       | S      | 0100011 / 000                   | mem[rs1+imm][7:0] = rs2[7:0] |
| 16 | BEQ      | B      | 1100011 / 000                   | if(rs1==rs2) PC += imm |
| 17 | BNE      | B      | 1100011 / 001                   | if(rs1!=rs2) PC += imm |
| 18 | BLT      | B      | 1100011 / 100                   | if(rs1<rs2) PC += imm (signed) |
| 19 | LUI      | U      | 0110111                         | rd = imm << 12 |
| 20 | JAL      | J      | 1101111                         | rd = PC+4; PC += imm |

### Pseudo-Komutlar

| Pseudo | Açılım                     | Açıklama |
|--------|----------------------------|----------|
| NOP    | ADDI x0, x0, 0             | İşlem yapma |
| MV rd, rs   | ADDI rd, rs, 0        | Register kopyala |
| LI rd, imm  | ADDI rd, x0, imm      | 12-bit immediate yükle |
| NEG rd, rs  | SUB rd, x0, rs        | İki'nin tümleyeni |
| J offset    | JAL x0, offset        | Koşulsuz dallanma |
| JR rs       | JALR x0, rs, 0        | Register'a sıçra |
| RET         | JALR x0, x1, 0        | ra'ya dön |
| CALL offset | JAL x1, offset        | Alt program çağır |
| BEQZ rs, off| BEQ rs, x0, off       | Sıfıra eşitse dallan |
| BNEZ rs, off| BNE rs, x0, off       | Sıfıra eşit değilse dallan |

### Direktifler

`.text`, `.data`, `.global` / `.globl`, `.word`, `.half`, `.byte`, `.string`,
`.space`, `.equ`, `.org`, `.end`, `.section`.

### İki Geçişli Akış

**Pass 1 — Layout & Symbol Definition:**
- LOCCTR (location counter) ile her komutun adresi hesaplanır.
- Etiketler SYMTAB'a girer (çift tanım kontrolü).
- `.global` direktifi sembolün binding'ini GLOBAL yapar.
- Bilinmeyen mnemonic'ler hata olarak raporlanır.

**Pass 2 — Code Generation & Relocation Detection:**
- Pseudo komutlar açılır, base komutlar encode edilir.
- Cross-file (extern) sembollere yapılan PC-relative referanslar için
  **relocation kaydı** oluşturulur (placeholder imm=0 ile encode edilir).
- Çıktı: `_object_codes` (adres-kod tuple list'i) + `_relocations` (linker için).

### Çıktı Formatları

- **SIC/XE Header–Text–End**: insan tarafından okunabilir nesne programı.
- **Flat binary** (`.bin`): doğrudan bellek imajı.
- **`.o.json`** (PICORV-OBJ v1): linker tarafından tüketilen yapılı format.

---

## Faz 2 — Linker Pipeline (2. Proje)

### Amaç

Birden fazla `.o.json` dosyasını birleştirip tek bir bellek imajı üretmek.
Symbol resolution, layout, relocation patching, error reporting.

### Object Dosya Formatı (`.o.json` — PICORV-OBJ v1)

JSON tabanlı (debug edilebilir, diff alınabilir). Şema:

```json
{
  "magic": "PICORV-OBJ",
  "version": 1,
  "source": "main.s",
  "sections": {
    ".text": { "size": 24, "data": "B7 02 00 10 13 03 00 00 ..." },
    ".data": { "size": 0,  "data": "" }
  },
  "symbols": [
    { "name": "_start", "section": ".text", "offset": 0,
      "binding": "GLOBAL", "defined": true },
    { "name": "delay_loop", "section": null, "offset": 0,
      "binding": "GLOBAL", "defined": false }
  ],
  "relocations": [
    { "section": ".text", "offset": 16,
      "type": "R_RISCV_JAL", "symbol": "delay_loop", "addend": 0 }
  ]
}
```

**Symbol section değerleri:**
- `.text` / `.data`: bu dosyanın ilgili section'ında tanımlı
- `.abs`: `.equ` ile tanımlı mutlak sabit
- `null`: tanımsız / harici (binding=GLOBAL + defined=false ⇒ extern)

### Desteklenen Relocation Tipleri

| Tip                    | Format etkilediği | Anlam                              | Durum |
|------------------------|--------------------|-------------------------------------|-------|
| `R_RISCV_JAL`          | J (JAL)            | 21-bit PC-relative dallanma        | ✅ Production |
| `R_RISCV_BRANCH`       | B (BEQ/BNE/BLT)    | 13-bit PC-relative koşullu dallanma | ✅ Production |
| `R_RISCV_HI20`         | U (LUI)            | sym[31:12] absolute (ile yuvarlama)| 🟡 İskelet |
| `R_RISCV_LO12_I`       | I (ADDI/LW…)       | sym[11:0] absolute                  | 🟡 İskelet |
| `R_RISCV_LO12_S`       | S (SW/SB)          | sym[11:0] absolute (S-format)      | 🟡 İskelet |
| `R_RISCV_PCREL_HI20`   | U (AUIPC)          | (sym-PC)[31:12] PC-relative        | 🟡 İskelet |
| `R_RISCV_PCREL_LO12_I` | I                  | PC-relative LO12                   | 🟡 İskelet |

JAL ve BRANCH **gerçek senaryoda doğrulanmıştır** (L-1, L-3 testleri ve
fiziksel FPGA çalıştırması). HI20/LO12 ailesi kodda tamam ama henüz
test edilmedi (gelecek iş — pseudo `LA` desteği ile birlikte).

### Linker Script Formatı

GNU ld'nin karmaşık DSL'i yerine basit `KEY = VALUE`:

```
TEXT_ORIGIN = 0x00000000
TEXT_LENGTH = 0x00002000
DATA_ORIGIN = 0x00002000
DATA_LENGTH = 0x00002000
ENTRY       = _start
```

Yorumlar `#` ile başlar. `int(val, 0)` kullandığımız için `0x..`, `0b..`,
`0o..` ve onluk hep desteklenir.

### Two-Pass Linker Mantığı

**Pass 1 — Layout & Symbol Resolution:**
1. Her objenin section'larını ardışık dizerek mutlak adres atar
   (text önce, sonra data; her dosyanın text'i bir öncekinin sonundan
   başlar; 4-byte hizalama).
2. Section image tamponları ayırılır, ham veriler kopyalanır
   (henüz yamasız — placeholder'lar imm=0).
3. Her dosyadaki sembol için:
   - `.abs` ise `offset` = mutlak adres
   - GLOBAL+defined ise `section_base + offset` ile global tabloya eklenir
   - Çift tanım hatası raporlanır
4. Her dosyadaki **extern** sembol global tabloda aranır; yoksa
   `undefined reference to 'X'` hatası.
5. Entry sembolü çözülür.

**Pass 2 — Relocation:**
- Her relocation kaydı için:
  - Sembolün mutlak adresi global tablodan alınır.
  - Tipe göre displacement / absolute hesaplanır
    (örneğin JAL: `disp = sym + addend - patch_abs`).
  - Range kontrolü (signed 13/21 bit aralığı, hizalama bit 0=0).
  - `bit_layout.py`'daki helper'larla immediate alanı paketlenir,
    eski makine kodunun ilgili maskesi temizlenip yeni değer OR'lanır.
  - Image tamponu yamanır.
- Her patching `_reloc_log`'a kaydedilir; `print_map()` ile rapor edilir.

### `bit_layout.py` — Encoder ile Linker Arasında DRY

B-format ve J-format immediate'ları RV32I'da rastgele dağıtılmış bit
konumlarına yerleştirilir (örn. J-format'ta imm[20|10:1|11|19:12]).
Bu paketlemeyi hem `encoder.py` hem `linker.py` kullanır. Tek bir
modülde toplandığı için **encoder ve linker matematiksel olarak garanti
tutarlı** — bir hata yapılırsa ikisi de aynı şekilde yapar.

```python
# bit_layout.py
B_IMM_MASK = 0xFE000F80   # B-format: 31, 30:25, 11:8, 7
J_IMM_MASK = 0xFFFFF000   # J-format: 31:12

def pack_b_imm(imm):    # 13-bit signed
    ...
def pack_j_imm(imm):    # 21-bit signed
    ...
```

Bu yapı bize bir kez gerçekten yardım etti: bir test EXPECTED dosyasında
elle hesapladığım `pack_j_imm(-4)` değeri yanlıştı (`0xFFFFF000` yerine
`0xFFDFF000` doğrusu). Encoder ve linker ortak modülü kullandığı için
ikisi de "doğru" değer üretti — hata sadece dış spec'te kaldı, koda
yansımadı. **Tek doğruluk kaynağı (single source of truth) prensibinin
pratik faydası.**

---

## Faz 3 — Test Matrisi ve CLI

### Regresyon Test Suite'i

`tests/link/` altında, byte-byte EXPECTED dosyalarıyla doğrulanan testler:

#### L-1: Cross-file `R_RISCV_JAL`

```
main.s:                         func.s:
  .global _start                  .global add5
  .global add5                    
  _start:                         add5:
    LI    a0, 10                    ADDI  a0, a0, 5
    JAL   ra, add5    ──reloc──→    RET
  done:
    JAL   x0, done
```

Linker `add5`'i func.o'da bulur, main.o'daki JAL'in placeholder'ını
(`0x000000EF`) hesaplanan displacement ile yamar (`0x008000EF`).

#### L-3: Cross-file `R_RISCV_BRANCH`

```
ping.s:                         pong.s:
  .global _start                  .global pong
  .global pong                    
  _start:                         pong:
    LI    a0, 0                     LI    a0, 99
    BEQZ  a0, pong   ──reloc──→     JAL   x0, pong
  skip:
    JAL   x0, skip
```

`BEQZ a0, pong` linker tarafında `BEQ a0, x0, +8` olarak çözülür.

#### Negatif Testler

- **Undefined reference**: Bir extern sembol hiçbir objede tanımlı değil
  → linker `undefined reference to 'X'` hatası verir, çıkış kodu ≠ 0.
- **Multiple definition**: Aynı GLOBAL sembol iki dosyada tanımlı
  → `Multiple definition of 'X': ... ve ...` hatası.
- **Missing entry**: Linker script'teki `ENTRY` sembolü tanımsız
  → `Entry sembolu '...' GLOBAL olarak tanimli degil` hatası.

### `run_link.py` — Tek Komutla Toolchain

```bash
python run_link.py <kaynak1> [<kaynak2> ...] [-T script.ld] [-o out_base] [-v]
```

* Kaynak `.s`/`.asm` ise **assemble** edilir (intermediate `.o.json` üretir).
* Kaynak `.o.json` ise **doğrudan linker'a geçer** (önceden assemble
  edilmiş objeler için).
* Çıktılar (`out_base` taban adıyla):
  * `out.bin`     — flat binary
  * `out.hex`     — Verilog `$readmemh` formatı
  * `out_init.vh` — Verilog `include` header (Faz 4'te eklendi, aşağıda)
  * `out.map.txt` — linker map raporu
* Hata durumunda map yine de üretilir (debug için), exit kodu 1.

Örnek:

```bash
python run_link.py firmware/blink/main.s firmware/blink/delay.s \
                   -T firmware/blink/tangnano9k.ld \
                   -o firmware/blink/build/blink -v
```

---

## Faz 4 — Tang Nano 9K SoC (FPGA Faz)

### Hedef

Toolchain'imizin ürettiği binary'yi **gerçek bir FPGA'da çalıştırmak**.
Bu sayede:

- Cross-file relocation'ların pratik kanıtı (L-1'in canlı versiyonu)
- `.bin` / `.hex` çıktılarının somut anlamı
- Linker script'in bellek haritasına dönüşmesi
- Toolchain → donanım entegrasyonu

### Donanım Seçimi

| Bileşen | Seçim | Sebep |
|---------|-------|-------|
| FPGA board | Sipeed **Tang Nano 9K** (GW1NR-LV9QN88PC6/I5) | Erişilebilir, eğitim amaçlı, 8640 LUT yeterli |
| FPGA aracı | **Gowin EDA Education Edition** | Tang Nano 9K resmi tool zinciri, ücretsiz lisans |
| CPU çekirdek | **PicoRV32** (Cliff Wolf, ISC) | Tek dosyalık RV32I, savaşta kanıtlı, akademik standart |
| Saat | 27 MHz on-board kristal osilatör | Tang Nano 9K'da hazır |
| Çıkış | 6× LED | Görsel doğrulama için yeterli |

### Yazılım Tarafı: LED Counter Demo

İki dosyalık demo program — **cross-file CALL relocation'ı** sahaya sürer:

```asm
# firmware/blink/main.s
.text
.global _start
.global delay_loop          # extern: delay.s'de tanımlı

_start:
    LUI   t0, 0x10000       # t0 = 0x10000000  (GPIO MMIO base)
    LI    t1, 0             # t1 = 0           (sayaç)

loop:
    SW    t1, 0(t0)         # *(GPIO) = sayaç  → LED'ler
    ADDI  t1, t1, 1         # sayaç++
    CALL  delay_loop        # JAL ra, delay_loop  → R_RISCV_JAL reloc
    J     loop              # JAL x0, loop        → yerel
```

```asm
# firmware/blink/delay.s
.text
.global delay_loop

delay_loop:
    LUI   t2, 0x400         # ~4.19M iterasyon, ~1 saniye @ 27 MHz
spin:
    ADDI  t2, t2, -1
    BNE   t2, x0, spin
    RET                     # JALR x0, x1, 0
```

```
# firmware/blink/tangnano9k.ld
TEXT_ORIGIN = 0x00000000
TEXT_LENGTH = 0x00002000
DATA_ORIGIN = 0x00002000
DATA_LENGTH = 0x00002000
ENTRY       = _start
```

`run_link.py` çıktısı (10 word, 40 byte):

| Adres | Hex | Decode | Açıklama |
|------:|----:|--------|----------|
| 0x00 | `100002b7` | LUI t0, 0x10000 | t0 = 0x10000000 (GPIO) |
| 0x04 | `00000313` | ADDI t1, x0, 0 | LI t1, 0 |
| 0x08 | `0062a023` | SW t1, 0(t0) | LED'lere yaz |
| 0x0C | `00130313` | ADDI t1, t1, 1 | sayaç++ |
| 0x10 | `008000ef` | JAL ra, +8 | **CALL delay_loop, +8 → 0x18 (linker tarafından çözüldü)** |
| 0x14 | `ff5ff06f` | JAL x0, -12 | J loop |
| 0x18 | `001003b7`/`004003b7` | LUI t2, 0x100/0x400 | delay sayım değeri |
| 0x1C | `fff38393` | ADDI t2, t2, -1 | spin sayaç-- |
| 0x20 | `fe039ee3` | BNE t2, x0, -4 | spin geri sıçra |
| 0x24 | `00008067` | JALR x0, x1, 0 | RET |

Linker map'inden alıntı:
```
Relocations applied (1):
  main.o.json .text@0x0010 R_RISCV_JAL  sym='delay_loop'
    resolved=0x00000018 patch_abs=0x00000010 old=0x000000EF new=0x008000EF
```

Yani assembler, `delay_loop`'un yerini bilmediği için `JAL ra, ?`'yi
placeholder olarak `0x000000EF` (rd=ra, imm=0) bıraktı. Linker iki obje
dosyasını birleştirip `delay_loop` adresini `0x18` olarak çözdü ve
displacement `+8` olduğu için J-format immediate'ı pakedi `0x008000EF`
ile yamadı. **Bu tam olarak bir gerçek linker'ın yaptığı şey.**

---

## Toolchain Komut Satırı Kullanımı

### Temel Akış

```bash
cd assembler_1/assembler_1
python run_link.py firmware/blink/main.s firmware/blink/delay.s \
                   -T firmware/blink/tangnano9k.ld \
                   -o firmware/blink/build/blink -v
```

Bu komut:
1. `main.s` → `main.o.json` (assemble)
2. `delay.s` → `delay.o.json` (assemble)
3. `*.o.json` → `blink.bin`, `blink.hex`, `blink_init.vh`, `blink.map.txt`
   (link + emit)
4. Entry: `0x00000000` raporlanır.

### Ayrı Aşamalar (Manuel)

Tek bir `.s`'yi sadece assemble etmek için:

```python
from assembler import assemble_file
asm, ok = assemble_file("foo.s")
asm.write_object("foo.o.json", source_name="foo.s")
asm.write_binary("foo.bin")
```

### Önceden Assemble Edilmiş Objeleri Linklemek

```bash
python run_link.py main.o.json delay.o.json -T script.ld -o build/firmware
```

`run_link.py` uzantıya göre ayırır (`.s/.asm` → assemble, `.json` → doğrudan).

### Çıktı Bayrakları

| Bayrak | Etki |
|--------|------|
| `--no-bin` | `.bin` çıktıyı atla |
| `--no-hex` | `.hex` çıktıyı atla |
| `--no-vh`  | `_init.vh` çıktıyı atla (Faz 4'te eklendi) |
| `--word-size {1,2,4}` | Verilog hex word boyutu (default 4) |
| `-v` / `--verbose` | Adım adım log |

---

## SoC Mimarisi ve Bellek Haritası

### Bellek Haritası

| Adres aralığı            | Aygıt | Açıklama                                                      |
|--------------------------|-------|---------------------------------------------------------------|
| `0x00000000-0x00001FFF`  | BRAM  | 8 KB blok bellek, picorv32 reset PC=0 ile birebir hizalı     |
| `0x10000000-0x100000FF`  | GPIO  | Yazma: alt 6 bit → LED'ler. Okuma: son yazılan değer.        |
| diğer                    | yok   | rdata=0 dönülür (CPU takılmasın diye fail-soft)              |

Adres decode `mem_addr[31:28]` üzerinden:
- `4'h0` → BRAM
- `4'h1` → GPIO
- diğer → no-op cevap

### Modüller

#### `bram.v` (60 satır)

- 32-bit kelime, ADDR_BITS=11 → 2048 kelime = 8 KB.
- Per-byte write strobe (`wstrb[3:0]`) — SB komutu için gerekli.
- Senkron okuma: `rdata <= mem[raddr]` posedge'de — Gowin BSRAM'a doğal
  infer edilir.
- **Init:** `\`include "blink_init.vh"` (toolchain tarafından üretilen),
  `$readmemh` yedek olarak.
- Header guard `BRAM_INIT_LOAD` ile dosya standalone derlenirse syntax
  hatasından korunur (Gowin gibi tool'lar .vh dosyalarını project source
  olarak compile ederse problem çıkmasın diye).

#### `gpio.v` (30 satır)

- MMIO peripheral. `sel` adres decode'undan gelir, herhangi bir
  byte-strobe set ise `wdata[5:0]` register'a yazılır.
- Soft tarafı "1=ON" semantik. Tang Nano 9K LED'leri **active-low**
  olduğu için inversion `soc_top.v`'de yapılır (`led_n = ~led_value`).

#### `soc_top.v` (130 satır)

- **Reset synchronizer**: 16 cycle power-on reset, sonra `btn_reset_n`
  active-low ile asenkron reset.
- **Bus**: PicoRV32'nin native MEM_VALID/MEM_READY interface'i.
- **1-cycle ready strobe**: BRAM senkron okuma yaptığı için ready'yi
  bir cycle gecikmeli üretiyoruz:
  ```verilog
  always @(posedge clk_27mhz)
      ready_d <= mem_valid && !ready_d;   // toggle her transaction'da
  assign mem_ready = ready_d;
  ```
- **Read mux**: `bram_sel ? bram_rdata : gpio_sel ? gpio_rdata : 0`.
- **PicoRV32 instance**: tüm ekstra özellikler (PCPI, IRQ, mul/div,
  compressed) **kapalı** — sadece RV32I.

### `blink_init.vh` — Toolchain ↔ Donanım Köprüsü

`run_link.py` her çalışmada üretiyor:

```verilog
// Auto-generated by run_link.py — DO NOT EDIT
`ifdef BRAM_INIT_LOAD
    mem[0] = 32'h100002b7;
    mem[1] = 32'h00000313;
    mem[2] = 32'h0062a023;
    mem[3] = 32'h00130313;
    mem[4] = 32'h008000ef;
    mem[5] = 32'hff5ff06f;
    mem[6] = 32'h004003b7;
    mem[7] = 32'hfff38393;
    mem[8] = 32'hfe039ee3;
    mem[9] = 32'h00008067;
`endif
```

`bram.v` içeriği:
```verilog
initial begin
    `define BRAM_INIT_LOAD
    `include "blink_init.vh"
    `undef BRAM_INIT_LOAD
    $readmemh(INIT_FILE, mem);   // yedek
end
```

Bu sayede `.s` dosyalarını değiştirip `run_link.py`'yi çalıştırmak,
yeni `blink_init.vh`'yi proje klasörüne kopyalamak ve Gowin'i tekrar
çalıştırmak yeterli — **`bram.v`'ye asla dokunmuyoruz.**

---

## Gowin Build Adımları

### 1) Gowin Projesi Oluştur

1. Gowin EDA → `File → New → FPGA Design Project`. Yer: `fpga/tangnano9k_soc/`.
2. Cihaz seçimi:
   - Series: **GW1NR**
   - Device: **GW1NR-LV9QN88PC6/I5**
   - Package: **QFN88**
   - Speed: **C6/I5**

### 2) Kaynak Dosyaları Ekle

`Design Sources` sekmesi → sağ tık → Add Files:

| Dosya | Tür |
|-------|-----|
| `vendor/picorv32/picorv32.v` | Verilog source |
| `fpga/tangnano9k_soc/bram.v` | Verilog source |
| `fpga/tangnano9k_soc/gpio.v` | Verilog source |
| `fpga/tangnano9k_soc/soc_top.v` | Verilog source (Top module olarak işaretle) |
| `fpga/tangnano9k_soc/blink_init.vh` | Verilog Include File (kritik — sadece include, compile değil!) |
| `fpga/tangnano9k_soc/tangnano9k.cst` | Physical constraint |
| `fpga/tangnano9k_soc/tangnano9k.sdc` | Timing constraint |

### 3) Sentez + Place & Route + Bitstream

`Process` panelinden `Run All`. Beklenen kaynak kullanımı:

- LUT: ~1100 / 8640 (~13%)
- FF: ~600 / 6480 (~9%)
- BSRAM: 4 / 26 (8 KB için)
- Fmax: > 80 MHz (27 MHz hedefin çok üstünde)

### 4) Yükleme

`Tools → Gowin Programmer`:

- **SRAM Program** — geçici test için (güç kesilince silinir)
- **Embedded Flash Program** — kalıcı (board her açıldığında çalışır)

Veya komut satırı:
```bash
openFPGALoader -b tangnano9k impl/pnr/blink_soc.fs       # SRAM
openFPGALoader -b tangnano9k -f impl/pnr/blink_soc.fs    # Flash
```

### 5) Beklenen Davranış

LED1..LED6 binary olarak ~1 saniye aralıkla sayar (LED1 her sn flip,
LED2 her 2 sn, ...). BTN1 (S1) basılınca reset → sayım sıfırdan başlar.

---

## Debug Yolculuğu (Karşılaştığımız Sorunlar)

Toolchain'i FPGA'da çalıştırırken peş peşe 4 sorun çıktı, hepsi öğretici:

### 1) `CT1136 — Bank 3 vccio çakışması`

**Hata:**
```
ERROR (CT1136) : Bank 3 vccio(1.8) is locked by other constraint or
embedded port, conflicting BANK_VCCIO set by 'led_n_X_obuf' :
IO_TYPE = LVCMOS33 in the same bank
```

**Sebep:** `.cst` dosyasında LED pinleri için `IO_TYPE=LVCMOS33` belirledim
ama Tang Nano 9K'da LED'lerin bağlı olduğu Bank 3 fiziksel olarak 1.8V
besleme ile çalışıyor (board hardware ve diğer pin constraint'leri bunu
zorluyor). 3.3V LVCMOS aynı bankta tanımlanamaz.

**Çözüm:** `LVCMOS33` → `LVCMOS18`. Tek karakter düzeltmesi, bir öğretici
ders: **FPGA bank voltajları silikondan değil board PCB tasarımından gelir**;
constraints'i board şemasına göre yazmak şart.

```
IO_PORT "led_n[0]" PULL_MODE=UP DRIVE=8 IO_TYPE=LVCMOS18;
```

### 2) `EX3934 — Loop count limit of 2000 exceeded`

**Hata:** `bram.v`'ye BRAM'ı sıfırlamak için bir for-loop eklemiştim:
```verilog
for (i = 0; i < (1<<ADDR_BITS); i = i + 1)
    mem[i] = 32'h00000000;
```
ADDR_BITS=11 → 2048 iterasyon. Ama Gowin GowinSynthesis'in default
loop unroll limiti **2000**. Bu hatayla aşıyor.

**Sebep:** Synthesis tool'ları `for` loop'larını **unroll** eder (donanımda
"loop" diye bir şey yok). 2048 iterasyonu açmaya çalışırken limit aşılıyor.

**Çözüm:** Loop'u tamamen kaldırdık. Gowin'in inferred BSRAM'ı
**specifiye edilmemiş hücreleri 0'a default'lar** zaten — explicit
sıfırlama gerekli değildi. Kodda sıfırlama varsayımı silindi, davranış
değişmedi.

### 3) `$readmemh` Sessizce Yok Sayıldı

**Belirti:** Tüm sentez başarıyla tamamlanır, bitstream yüklenir, ama
LED'ler hiç yanmaz. CPU sürekli `0x00000000 = ADDI x0, x0, 0` (NOP)
çalıştırıyor — yani **BRAM tamamen sıfır.**

**Sebep:** `$readmemh("blink.hex")` Verilog standart bir işlevdir ama
Gowin GowinSynthesis bazı durumlarda dosyayı **sessizce** (uyarı bile
vermeden) yok sayıyor. Bu bilinen bir problem — birçok Gowin kullanıcısı
aynı şeyle karşılaşmış.

**Aşama 1 çözüm (geçici):** `bram.v`'ye blink.hex'in içeriğini elle
inline hardcode olarak ekledik. LED'ler çalıştı ama bu **toolchain'i
bypass ediyor** — yeni bir program yazdığımızda otomatik güncellenmiyor.

**Aşama 2 doğrulama:** "Toolchain gerçekten çalışıyor mu?" testini
yaptık — `delay.s`'de `LUI t2, 0x100` → `LUI t2, 0x400` (4× yavaşlatma),
`run_link.py` ile yeni `blink.hex` ürettik, ama `bram.v`'deki inline
değerleri **değiştirmedik**. Sentez sonrası LED'ler **eskisi gibi hızlı**
saydı → `$readmemh` ignore edildiği kanıtlandı.

**Aşama 3 nihai çözüm:** Toolchain'e ek bir çıktı format ekledik:
**`blink_init.vh`** — `mem[i] = 32'h...;` şeklinde explicit Verilog
deyimleri. `bram.v` bu dosyayı `\`include` ediyor. Preprocessor
seviyesinde işlenir, sentez tool'ı ne yapıyorsa yapsın init data
kesin garanti yüklenir.

```python
# hex_emitter.py
def write_verilog_init(image, path, ...):
    """run_link.py her çalıştığında üretir; bram.v include eder."""
    ...
```

### 4) `EX3863 — Syntax error near '='` (Standalone Compile Sorunu)

**Hata:** `blink_init.vh`'yi Gowin'e "Add Files" ile eklediğimde,
Gowin onu **standalone Verilog modülü** olarak parse etmeye çalıştı.
İçindeki `mem[i] = 32'h...;` deyimleri sadece `initial begin`-`end`
içinde geçerli; module-level olarak yazılırsa syntax error.

**Çözüm:** Header guard pattern. Toolchain üretimini guard ile sardık:

```verilog
`ifdef BRAM_INIT_LOAD
    mem[0] = 32'h100002b7;
    ...
`endif
```

`bram.v`:

```verilog
initial begin
    `define BRAM_INIT_LOAD
    `include "blink_init.vh"   // burada BRAM_INIT_LOAD tanımlı, içerik aktif
    `undef BRAM_INIT_LOAD
end
```

Gowin dosyayı standalone derlerse `BRAM_INIT_LOAD` tanımlı değil →
içerik atlanır → file boş kabul edilir → hata yok. `\`include` ile
çağrıldığında guard tanımlı → init data gerçekten yüklenir.

Bu **C/C++'taki `#ifndef HEADER_H / #define HEADER_H / #endif` pattern**'inin
Verilog karşılığı. Akademik açıdan da hoş bir köprü.

---

## Doğrulama Metodolojisi

### Test Matrisi

| Test          | Tip                | Cross-file? | Yöntem | Durum |
|---------------|--------------------|-------------|--------|-------|
| L-1 basic JAL | R_RISCV_JAL        | ✓           | Byte-byte EXPECTED ile karşılaştırma | ✅ |
| L-3 cross BR  | R_RISCV_BRANCH     | ✓           | Byte-byte EXPECTED ile karşılaştırma | ✅ |
| Negatif: undef ref | —             | —           | Hata mesajı + exit code        | ✅ |
| Negatif: multi def | —             | —           | Hata mesajı + exit code        | ✅ |
| Negatif: missing entry | —         | —           | Hata mesajı + exit code        | ✅ |
| FPGA: blink   | R_RISCV_JAL (CALL) | ✓           | **Fiziksel LED gözlemi**       | ✅ |
| FPGA: $readmemh test | (toolchain) | ✓        | Davranış değişti mi gözlemi    | ✅ (✗ → .vh fix) |

### Linker Map Çıktısı

`run_link.py` her çalışmasında `out.map.txt` üretir:

```
========================================================================
LINK MAP
========================================================================
Script: LinkerScript(text=0x00000000+8192, data=0x00002000+8192, entry='_start')

Section Bases:
  .text    0x00000000 - 0x00000018  (  24B)  firmware/blink/main.o.json
  .text    0x00000018 - 0x00000028  (  16B)  firmware/blink/delay.o.json

Symbols (defined):
  _start           0x00000000  GLOBAL  .text     firmware/blink/main.o.json
  loop             0x00000008  LOCAL   .text     firmware/blink/main.o.json
  delay_loop       0x00000018  GLOBAL  .text     firmware/blink/delay.o.json
  spin             0x0000001C  LOCAL   .text     firmware/blink/delay.o.json

Entry: _start @ 0x00000000

Relocations applied (1):
  firmware/blink/main.o.json .text@0x0010 R_RISCV_JAL
    sym='delay_loop' resolved=0x00000018 patch_abs=0x00000010
    old=0x000000EF new=0x008000EF
```

Bu rapor **her ödev sunumu için hazır kanıt** — sembollerin nereye gittiği,
relocation'ın hangi byte'ı nasıl yamadığı net yazıyor.

---

## Lisanslar ve Atıflar

- **Bizim kod (assembler, linker, hex_emitter, soc_top, bram, gpio, demo
  firmware):** Akademik proje — repo lisansı dilediğiniz gibi
  belirleyebilir (önerilen: MIT veya CC0).
- **PicoRV32** (`vendor/picorv32/picorv32.v`): Cliff Wolf, ISC License.
  `vendor/picorv32/COPYING` dosyasında lisans metni mevcut. ISC sadece
  copyright notice'ın korunmasını ister; hem kaynak kodda hem repoda zaten
  mevcut. Akademik dürüstlük: README'de ve raporda atıf yapılmalı.

---

## Gelecek İşler

1. **L-2 testi (HI20/LO12)** — Pseudo `LA rd, label` desteği assembler'a
   eklenince absolute address yükleme test edilir. `R_RISCV_HI20` ve
   `R_RISCV_LO12_I` zaten linker'da iskelet halinde; eksik olan tek şey
   pseudo'nun `LUI + ADDI` çiftine açılması.
2. **`.data` aktivasyonu** — Şu an firmware sadece `.text` kullanıyor.
   `.data` ile global değişken init'i, SW/LB testi.
3. **UART peripheral** — GPIO yerine veya yanına bir TX/RX modülü;
   "Hello World" yazılım programı.
4. **Test runner** — `tests/link/` altındaki testleri otomatik koşturan
   bir `pytest` veya saf-Python harness. Şu an manuel inspection ile.
5. **`__pycache__/*.pyc` cleanup** — Geçmiş commitlerde yanlışlıkla
   eklendi, `.gitignore`'da olmasına rağmen tracked. `git rm --cached`
   ile temizlenebilir.

---

## Kısa Kullanım Özeti

```bash
# 1. Yazılım derle
cd assembler_1/assembler_1
python run_link.py firmware/blink/main.s firmware/blink/delay.s \
                   -T firmware/blink/tangnano9k.ld \
                   -o firmware/blink/build/blink

# 2. Çıktıları FPGA proje klasörüne kopyala
cp firmware/blink/build/blink.hex      fpga/tangnano9k_soc/blink.hex
cp firmware/blink/build/blink_init.vh  fpga/tangnano9k_soc/blink_init.vh

# 3. Gowin'de Run All → Tools → Programmer → SRAM Program

# 4. Tang Nano 9K'da LED'ler ~1 saniye arayla sayar
```

Her assembly değişikliğinden sonra adım 1-3 — `bram.v`'ye veya başka bir
Verilog dosyasına dokunmadan. **Toolchain ile donanım birbirinden bağımsız.**

---

*Sistem Programlama Dersi — Birleşik Proje*
