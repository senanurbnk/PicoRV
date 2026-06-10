# Proje 3 — Sunum Çalışma Kılavuzu (Savunma Hazırlığı)

> Bu dosya, sunumda ve bireysel Q&A'da hâkim olman için hazırlanmıştır. Her modülün
> **ne yaptığı, hangi dosyada olduğu, nasıl çalıştığı** ve hocanın sorabileceği
> **"şunu değiştir bakalım"** senaryolarının cevabı burada. Sonunda muhtemel sorular ve
> komut kopya kâğıdı var.
>
> **Çalışma dizini:** `assembler_1/assembler_1/`
> **Repo:** github.com/senanurbnk/PicoRV  |  **Kart:** Tang Nano 9K (Gowin GW1NR-9)

---

## 0. 30 saniyelik özet (ezberle)

> "RISC-V PicoRV32 işlemcisi için **kendi assembler, linker ve bootstrap loader'ımızı**
> yazdık. Bilgisayardan UART üzerinden, **CRC-16 ile korunan paketlerle** program
> gönderiyoruz; FPGA'daki loader bunu **RAM'e (0x3000) yazıp** programın başlangıç adresine
> **JALR ile atlayarak** çalıştırıyor. Loader, **işlemcinin kendi RV32I komut setiyle**
> yazıldı ve **kendi araç zincirimizle** derlendi. Tüm sistemi, sentezden önce yazdığımız
> bir **komut-set simülatöründe (ISS)** doğruladık, sonra Tang Nano 9K'da fiziksel
> çalıştırdık."

**En kritik tek cümle (RAM/loader sorusu gelirse):** "Loader bir donanım değil, BRAM'in
0x0000 adresinde duran ve PicoRV32'nin koşturduğu bir **yazılımdır**; UART'tan gelen
uygulamayı BRAM'in 0x3000 bölgesine yazar ve oraya atlar."

---

## 1. Büyük Resim: İki Dünya

| | Sol: PC (derleme zamanı) | Sağ: FPGA (çalışma zamanı) |
|---|---|---|
| Ne olur | Kaynak kod → makine kodu → paket | Paketler RAM'e yazılır, CPU çalıştırır |
| Dil | Python (toolchain) | Verilog (donanım) + RV32I (loader) |
| Çıktı | `.bin` / `.hex` / `_init.vh` | LED yanması, UART ACK'leri |

Köprü = **UART** (seri kablo). Tüm akış:

```
uygulama.s → ASSEMBLER → .o.json → LINKER → .bin → HOST_LOADER →UART→ LOADER → RAM(0x3000) → JUMP → çalışır
```

---

## 2. Repo Haritası — Ne Nerede?

```
assembler_1/assembler_1/
├── TOOLCHAIN (Python, derleme zamanı)
│   ├── opcode_table.py     # 23 RV32I komutu + 10 pseudo komut tablosu
│   ├── register_table.py   # x0..x31 ve ABI isimleri (a0, t0, ra...)
│   ├── parser.py           # satır ayrıştırma: etiket/komut/operand/bellek
│   ├── encoder.py          # 6 RV32I formatını 32-bit makine koduna çevirir
│   ├── bit_layout.py       # B/J/I/S/U immediate bit dağıtımı (encoder+linker ortak)
│   ├── symbol_table.py     # etiket→adres; LOCAL/GLOBAL binding
│   ├── assembler.py        # iki geçişli assembler (ana modül); .o.json üretir
│   ├── object_format.py    # .o.json şeması (PICORV-OBJ): section/symbol/relocation
│   ├── linker_script.py    # KEY=VALUE bellek haritası okuyucu (.ld)
│   ├── linker.py           # iki geçişli linker: layout + relocation
│   ├── hex_emitter.py      # .bin / .hex / _init.vh çıktıları
│   └── run_link.py         # CLI: assemble+link+emit tek komut
│
├── LOADER (RV32I — FPGA'da koşan sistem yazılımı)
│   ├── loader/loader.s         # 82 komut / 328 bayt bootstrap loader
│   ├── loader/loader.ld        # boot bölgesi linker script (0x0000)
│   ├── loader/build_loader.py  # loader'ı derle + SoC'a mem_init.vh olarak kur
│   └── loader/test_loader.py   # ISS ile FPGA'sız doğrulama
│
├── HOST (PC tarafı yükleyici)
│   ├── host/crc.py          # CRC-16/CCITT-FALSE (loader ile birebir)
│   ├── host/packet.py       # paket çerçeveleme (SYNC|CMD|LEN|ADDR|DATA|CRC)
│   └── host/host_loader.py  # pyserial; gönder, ACK/NAK, retry
│
├── DOĞRULAMA
│   └── tools/iss.py         # RV32I komut-set simülatörü (sentez öncesi test)
│
├── UYGULAMALAR (UART'tan yüklenen test programları)
│   ├── apps/t1_arith_led.s    # aritmetik + LED
│   ├── apps/t2_loop_blink.s   # döngü + sayaç
│   ├── apps/t3_func_button.s  # fonksiyon çağrısı + buton
│   └── apps/app.ld            # uygulama linker script (0x3000)
│
└── DONANIM (Verilog SoC)
    └── fpga/tangnano9k_soc/
        ├── soc_top.v       # üst modül: CPU + bus + adres çözücü + reset/clk
        ├── bram.v          # 16 KB blok bellek (RAM), mem_init.vh ile gömülü
        ├── uart.v          # 8N1 UART (TX+RX), MMIO
        ├── gpio.v          # LED çıkış + buton giriş, MMIO
        ├── tangnano9k.cst  # pin atamaları
        ├── tangnano9k.sdc  # 27 MHz zamanlama kısıtı
        ├── mem_init.vh     # BRAM init (loader/echo — toolchain üretir)
        └── vendor/picorv32/picorv32.v  # CPU çekirdeği (Cliff Wolf, ISC)
```

---

## 3. Toolchain — Modül Modül (Proje 3 ağırlıklı)

### 3.1 `opcode_table.py` — Komut Tablosu
Her RV32I komutunun **opcode / funct3 / funct7** alanlarını tutar. Sözlük (hash map) yapısı.
- **20 → 23 komut:** Proje 3'te **XOR (R), XORI (I), LBU (I-load)** eklendi.
  - *Neden XOR?* CRC-16 hesabı temelde XOR'dur; loader'ı RV32I'da yazabilmek için gerekti.
  - *Nasıl eklendi?* Sadece bu dosyaya 3 satır; encoder/assembler **değişmedi** (format-genel).
- 6 format: R, I, S, B, U, J. 10 pseudo komut: `NOP, MV, LI, NEG, J, JR, RET, CALL, BEQZ, BNEZ`.

### 3.2 `parser.py` — Ayrıştırıcı
Bir assembly satırını parçalara böler: **etiket** (`loop:`), **komut** (`ADD`), **operandlar**.
- 4 operand tipi: `register` (x5/t0), `immediate` (42, 0x10), `symbol` (etiket adı),
  `memory` (`8(t0)` = offset(register)).
- Yorumları (`#`, `;`) atar, `.text`/`.global` gibi direktifleri tanır.
- Önemli ayrım: `.` ile başlayan = **direktif**, değilse = **komut**.

### 3.3 `encoder.py` + `bit_layout.py` — Makine Kodu Üretimi
- `encoder.py`: format tipine göre 32-bit kelimeyi oluşturur (opcode/funct/register/immediate
  alanlarını yerleştirir).
- `bit_layout.py`: RV32I'da B ve J formatlarındaki immediate **dağıtık** durur (bitler
  karışık yerlerde). `pack_b_imm`, `pack_j_imm` bunu yapar. **Kritik:** bu fonksiyonlar
  hem encoder hem linker tarafından kullanılır → ikisi matematiksel olarak **garanti
  tutarlı**. (Tek doğruluk kaynağı = DRY prensibi.)

### 3.4 `symbol_table.py` — Sembol Tablosu
Etiketleri adreslerle eşler. Proje 2/3'te eklenen: **binding** alanı.
- `LOCAL`: sadece bu dosyada görünür.
- `GLOBAL`: dışa açık (`.global` direktifi).
- `EXTERN` = GLOBAL + henüz tanımsız (başka dosyada tanımlı olmalı → linker çözer).

### 3.5 `assembler.py` — İki Geçişli Assembler (ana modül)
- **Pass 1 (Layout):** LOCCTR (konum sayacı) ile her komutun adresini hesaplar, etiketleri
  sembol tablosuna yazar, çift tanımı yakalar.
- **Pass 2 (Code Gen):** her komutu encode eder. Başka dosyadaki bir sembole referans
  (extern) varsa, makine kodunu **immediate=0 placeholder** ile üretir ve bir
  **relocation kaydı** oluşturur ("bu adresteki şu komut, şu sembol için sonra yamanacak").
- Çıktı: `.o.json` (`to_object_file()` / `write_object()`).

### 3.6 `object_format.py` — Nesne Dosyası Formatı (`.o.json`)
Özgün formatımız: **PICORV-OBJ** (JSON tabanlı). İçinde:
- `sections`: `.text` / `.data` ham baytları.
- `symbols`: ad, section, offset, binding, defined.
- `relocations`: section, offset, tip (R_RISCV_JAL...), sembol, addend.
- **Neden JSON?** Gözle okunabilir, diff alınabilir, hata ayıklaması kolay. (Savunma: "üretim
  ortamı ELF kullanır; biz akademik şeffaflık için JSON seçtik.")

### 3.7 `linker_script.py` — Bellek Haritası (.ld)
Basit `KEY = VALUE` format (GNU ld'nin karmaşık DSL'i yerine):
```
TEXT_ORIGIN = 0x00003000
TEXT_LENGTH = 0x00000800
DATA_ORIGIN = 0x00003800
ENTRY       = _start
```
Linker buradan section'ların başlangıç adreslerini ve giriş noktasını okur.

### 3.8 `linker.py` — İki Geçişli Linker (EN ÖNEMLİ — hoca buradan sorar)
**Pass 1 — Layout & Symbol Resolution:**
1. Her `.o.json`'un section'larını **ardışık** yerleştirir (text'ler arka arkaya, 4-byte
   hizalı), her birine mutlak **base adres** atar.
2. GLOBAL+tanımlı her sembol için **mutlak adres = base + offset** hesaplar, global tabloya
   ekler. **Çift tanım** → "multiple definition" hatası.
3. Her EXTERN sembolü global tabloda arar. Yoksa → **"undefined reference"** hatası.
4. Giriş sembolünü (`_start`) çözer.

**Pass 2 — Relocation (yama):**
- Her relocation kaydı için: sembolün mutlak adresini alır, **tipe göre** değeri hesaplar,
  makine kodunun ilgili bitlerini yamar (`bit_layout` ile). Desteklenen tipler:

| Tip | Ne yapar | Durum |
|---|---|---|
| `R_RISCV_JAL` | `disp = hedef − PC`, 21-bit, J-format | ✅ Production |
| `R_RISCV_BRANCH` | `disp = hedef − PC`, 13-bit, B-format | ✅ Production |
| `R_RISCV_HI20 / LO12` | mutlak adres (LUI+ADDI) | 🟡 İskelet |

**Somut örnek (L1 testi — ezberle):** `JAL ra, add5`
- `add5` mutlak adresi = `0x0000000C`, komut adresi (PC) = `0x00000004`
- `disp = 0x0C − 0x04 = +8`
- `pack_j_imm(8) = 0x00800000`
- Yamasız kod `0x000000EF` (rd=ra, imm=0) → **yamalı kod `0x008000EF`**
- Bu, "linker'ın boş bıraktığı atlama mesafesini doldurması" işleminin tam kanıtı.

### 3.9 `hex_emitter.py` — Çıktı Üreticileri
- `.bin`: ham baytlar (host'un göndereceği).
- `.hex`: Verilog `$readmemh` formatı.
- `_init.vh`: BRAM'i sentezde dolduran `mem[i]=32'h...;` satırları (**kritik köprü**, §5.4).

### 3.10 `run_link.py` — CLI
Tek komutla zinciri koşturur: `.s` → assemble → `.o.json` → link → `.bin/.hex/_init.vh/.map.txt`.

---

## 4. Host (PC) Tarafı

### 4.1 `crc.py` — CRC-16/CCITT-FALSE
- Parametreler: polinom `0x1021`, başlangıç `0xFFFF`, **yansımasız (MSB-first)**, xorout 0.
- Kontrol değeri: `CRC("123456789") = 0x29B1` (standart doğrulama).
- **Neden yansımasız?** Çünkü loader RV32I'da bunu birebir yazabilsin (sola kaydır, bit15
  test, koşullu `XOR 0x1021`).
- **Neden CRC, checksum değil?** CRC ardışık (burst) bit hatalarını çok daha güçlü yakalar.

### 4.2 `packet.py` — Paket Çerçeveleme
`SYNC(AA55) | CMD | LEN | ADDR(4 LE) | DATA | CRC16(2)`.
- CMD: `0x01`=WRITE_BLOCK, `0x02`=START(jump), `0x03`=PING.
- CRC, **SYNC hariç** CMD..DATA üzerinden. Blok boyu 4'ün katı (word hizalı).

### 4.3 `host_loader.py` — Yükleyici
`pyserial` ile: `.bin`'i bloklara böl → her bloğu WRITE paketi yap → gönder → **ACK (0x06)**
bekle → NAK'ta **yeniden gönder** (retry) → bitince **START** paketi.
Komut: `python host_loader.py --port COM5 --baud 9600 --bin ../apps/t1.bin --addr 0x3000 --entry 0x3000`

---

## 5. Donanım (FPGA SoC) — Verilog

### 5.1 `soc_top.v` — Üst Modül (her şeyi bağlar)
- **Adres çözücü:** `mem_addr[31:28]` → `0`=BRAM, `1`=GPIO, `2`=UART, diğer→0.
- **Reset senkronizatörü:** 16-cycle güç-açılış + buton → `resetn` üretir.
- **Bus:** PicoRV32 native arayüzü `mem_valid` / `mem_ready` / `mem_wstrb` / `mem_addr` / `mem_wdata` / `mem_rdata`.
- **Read mux:** seçilen bloğun verisini CPU'ya döndürür.
- **PicoRV32 parametreleri:** `PROGADDR_RESET=0x0` (reset'te buradan başlar), `STACKADDR=0x2000`, RV32I-only (mul/div/irq/compressed kapalı).

### 5.2 `bram.v` — RAM (hoca "RAM nedir, nasıl init oluyor?" diye sorabilir)
- **16 KB** (`ADDR_BITS=12`, 4096 × 32-bit kelime). Per-byte write-strobe (SB komutu için).
- Senkron okuma: `rdata <= mem[raddr]` (1 cycle gecikme → bu yüzden `ready` 1 cycle gecikmeli).
- **Init:** `\`include "mem_init.vh"` — başlangıç içeriği (loader) sentezde gömülür.
- Bölünme: `0x0000–0x0FFF` loader, `0x3000–0x3FFF` uygulama.

### 5.3 `uart.v` — Seri Haberleşme (MMIO 0x2000_0000)
- **8N1:** 1 start + 8 veri (LSB-first) + 1 stop. Baud bölücü `DIV = CLK_FREQ/BAUD` (27MHz/9600).
- **TX:** kaydırmalı yazmaç. **RX:** start kenarı yakala, **orta-bit örnekleme**, 2-FF senkronizer.
- Register: `+0 DATA` (oku=rx byte, yaz=tx byte), `+4 STATUS` (bit0=rx_valid, bit1=tx_busy).
- **Yazılım sözleşmesi:** TX'ten önce tx_busy=0 bekle; rx_valid=1 olunca DATA oku.

### 5.4 `mem_init.vh` köprüsü (Proje 3'ün en kritik debug hikâyesi)
- **Sorun:** Standart `$readmemh` Gowin sentez aracında **sessizce yok sayılıyordu** → BRAM
  sıfır kalıyor → CPU NOP koşuyor → LED yanmıyor.
- **Çözüm:** `hex_emitter`, loader'ı açık `mem[0]=32'h...; mem[1]=...;` Verilog deyimlerine
  çeviren `mem_init.vh` üretiyor; `bram.v` bunu `\`include` ediyor. Header-guard (`\`ifdef
  BRAM_INIT_LOAD`) ile dosya standalone derlenince hata vermiyor.

### 5.5 `gpio.v` — LED + Buton (MMIO 0x1000_0000)
- `+0 LED`: yaz → alt 6 bit LED'lere. `+4 buton`: oku → bit0.
- LED'ler active-low: `led_n = ~led_value` (soyutlama: yazılım "1=yak" görür).
- Buton: active-low, 2-FF senkronize edilip terslenir ("1=basılı").

### 5.6 Pin atamaları (`tangnano9k.cst`)
clk=52, reset=4, buton=3, LED=10/11/13/14/15/16, uart_tx=17, uart_rx=18.

---

## 6. Loader — `loader/loader.s` (RV32I, hoca buradan kesin sorar)

**82 komut / 328 bayt, tek dosya, stack kullanmaz** (leaf altprogramlar). FSM:
```
RESET(PC=0) → IDLE → SYNC(AA,55) → HEADER(CMD,LEN,ADDR×4)
            → DATA döngüsü (b=getc; SB b→[ptr]; crc; i++) → CRC karşılaştır
            → eşit & START? → JUMP 0x3000 / değilse → ACK
            → eşit değil → NAK → IDLE
```
**Register kullanımı:** `s0`=UART base, `s1`=crc, `s2`=cmd, `s3`=len, `s4`=addr,
`s5`=rx_crc, `s6`=i, `s7`=ptr. Leaf altprogramlar: `getc`, `putc`, `crc16_byte`.

**JUMP:** `JALR x0, 0(s4)` → uygulamanın giriş adresine (0x3000) atlar. Bu, hocanın
bahsettiği "işlemciyi serbest bırakma"nın yazılımsal karşılığı.

---

## 7. ISS — `tools/iss.py` (özgünlük; "nasıl test ettiniz?" sorusu)
- Bizim yazdığımız **RV32I komut-set simülatörü**. Linker'ın ürettiği **gerçek makine
  kodunu** çalıştırır; UART ve GPIO'yu modeller.
- `test_loader.py`: gerçek `loader.bin`'i host paketleriyle besler → loader'ın app'i 0x3000'e
  **bayt-bayt** yazdığını, **ACK'lediğini** (= loader CRC'si host CRC'si ile birebir), **jump**
  ettiğini ve **bozuk CRC'de NAK→retransmit** yaptığını kanıtlar — **sentez olmadan**.

---

## 8. Test Uygulamaları (`apps/`)
| Test | Ne yapar | Test ettiği |
|---|---|---|
| `t1_arith_led.s` | 40+2=42 → LED (`0b101010`) | en basit yükleme kanıtı |
| `t2_loop_blink.s` | 6-bit sayaç + gecikme döngüsü | döngü, BNE/J, zamanlama |
| `t3_func_button.s` | `get_button()` (JAL/RET) + butona göre LED | fonksiyon çağrısı, GPIO girişi |

---

## 9. 🔴 "HOCA ŞUNU DEĞİŞTİR BAKALIM" SENARYOLARI (en kritik bölüm)

**ALTIN KURAL — ezberle:**
> **Uygulama** değişikliği → sadece **yeniden link + UART'tan yeniden yükle** (sentez YOK, ~saniyeler).
> **Donanım veya loader** değişikliği → **yeniden sentez + bitstream yükleme** gerekir (Gowin, ~dakikalar).

| Hoca derse ki... | Nerede değiştirirsin | Sentez gerekir mi? | Adımlar |
|---|---|---|---|
| **"LED desenini/sonucu değiştir"** | `apps/t1_arith_led.s` (`LI t1, 40` → başka) | ❌ Hayır | `run_link` → `host_loader` ile yeniden yükle |
| **"Blink hızını değiştir"** | `apps/t2_loop_blink.s` (`LUI t3, 0x8` → büyüt) | ❌ Hayır | `run_link` → yeniden yükle |
| **"Buton davranışını tersle"** | `apps/t3_func_button.s` (`BEQ`→`BNE` veya LI değerleri) | ❌ Hayır | `run_link` → yeniden yükle |
| **"Uygulamayı başka adrese yükle"** | `apps/app.ld` (`TEXT_ORIGIN`) + host `--addr/--entry` | ❌ Hayır (BRAM içindeyse) | `run_link -T app.ld` → `host_loader --addr 0xYYYY` |
| **"Assembler'a yeni komut ekle"** | `opcode_table.py` (3 satır, XOR gibi) | ❌ Hayır | komut tablosuna ekle; uygulamada kullan; `run_link` |
| **"Baud'u 115200 yap"** | `soc_top.v` `UART_BAUD` | ✅ Evet | değiştir → src'e kopyala → Gowin Run All → flash → `host --baud 115200` |
| **"RAM'i büyüt/küçült"** | `bram.v` `ADDR_BITS` + `soc_top` adres bitleri + `.ld` LENGTH | ✅ Evet | değiştir → yeniden sentez |
| **"Yeni bir LED/pin bağla"** | `tangnano9k.cst` (+ gpio genişlet) | ✅ Evet | pin ekle → yeniden sentez |
| **"Loader davranışını değiştir"** | `loader/loader.s` | ✅ Evet (loader gömülü) | `build_loader.py --install` → yeniden sentez → flash |
| **"CRC'yi checksum yap"** | `host/crc.py` **VE** `loader.s` `crc16_byte` | ✅ Evet (loader) | ikisi de **birebir** değişmeli; loader gömülü → sentez |

**Demo'da en etkileyici cevap:** "LED desenini değiştir" derse → `apps/t1`'i düzenle, `run_link`
çalıştır, `host_loader` ile **canlı yükle**, LED birkaç saniyede değişir — **sentez yok**.
Bu, loader mimarisinin asıl gücünü gösterir (donanımı her seferinde yeniden derlemiyoruz).

### Örnek: T1'i değiştir
`apps/t1_arith_led.s` içinde sayıyı/işlemi değiştir:
```
LI t1, 50
LI t2, 8
SUB t3, t1, t2     # 50-8 = 42 (LED deseni 0b101010) ya da farklı bir sayı
SW t3, 0(t0)
```
Sonra:
```
python run_link.py apps/t1_arith_led.s -T apps/app.ld -o apps/t1_arith_led
cd host && python host_loader.py --port COM5 --baud 9600 --bin ../apps/t1_arith_led.bin --addr 0x3000 --entry 0x3000
```

---

## 10. Muhtemel Sorular ve Cevapları

**S: RAM nedir, nerede, nasıl başlatılıyor?**
C: BRAM = FPGA içi blok bellek (`bram.v`, 16 KB). Hem kod hem veri burada. Loader 0x0000'da,
uygulama 0x3000'de. Başlangıç içeriği (loader) sentezde `mem_init.vh` ile gömülür; uygulama
çalışma anında UART'tan dolar.

**S: Linker tam olarak ne yapıyor?**
C: Birden çok nesne dosyasını birleştirip adresleri kesinleştirir. Pass 1'de section'ları
yerleştirip sembollere mutlak adres atar; Pass 2'de çözülmemiş referansları (relocation)
yamar. Örnek: `JAL ra, add5` → `0x000000EF` → `0x008000EF`.

**S: Relocation neden gerekli?**
C: Assembler tek dosyayı bilir; başka dosyadaki bir sembolün adresini bilemez, yerini boş
bırakır (imm=0) ve "burayı sonra doldur" notu (relocation) düşer. Linker tüm dosyaları
görünce adresi bilir ve yamar.

**S: İki dosya aynı global sembolü tanımlarsa?**
C: Linker Pass 1'de "multiple definition" hatası verir. Hiç tanımlanmazsa "undefined reference".

**S: Neden iki geçiş (two-pass)?**
C: İleri referans (forward reference): bir sembol kullanıldığı yerden sonra tanımlanabilir.
Tek geçişte adresi bilemezsin. Pass 1 tüm adresleri toplar, Pass 2 kullanır.

**S: Endianness?**
C: RV32I little-endian. Host'un bayt sırası ile loader'ın `SB` yazımı uyumlu. ISS'te RAM
geri-okumasıyla doğruladık.

**S: CRC neden checksum değil?**
C: CRC polinom bölmesi tabanlı; ardışık bit hatalarını çok daha güçlü yakalar. CRC-16/CCITT
16 bite kadar burst hatayı kesin yakalar.

**S: Loader donanım mı yazılım mı?**
C: **Yazılım.** PicoRV32'nin kendi RV32I komutlarıyla yazıldı, BRAM'de 0x0000'da duruyor,
CPU onu çalıştırıyor. Hocanın "işlemciyi reset'te tut" ifadesi = uygulama loader atlayana
kadar başlamaz; "serbest bırak" = `JALR` ile 0x3000'e atlama.

**S: $readmemh neden çalışmadı, ne yaptınız?**
C: Gowin onu sessizce yok sayıyordu (BRAM sıfır kalıyordu). Çözüm: toolchain'in açık
`mem[i]=...` deyimleri üreten `mem_init.vh` dosyası + `\`include`.

**S: UART nasıl çalışıyor, baud nedir?**
C: 8N1 seri protokol. Baud = saniyedeki bit. FPGA'da baud sentez-zamanı sabit (`UART_BAUD`,
`DIV=CLK_FREQ/BAUD`). Host ve FPGA aynı baud'da olmalı; bu yüzden 115200 için yeniden sentez
gerekir.

**S: Adres çözücü nasıl karar veriyor?**
C: `mem_addr[31:28]` (üst 4 bit): 0→BRAM, 1→GPIO, 2→UART. MMIO mantığı: tek adres uzayı,
farklı bölgeler farklı donanıma gider.

**S: Neden kendi assembler/linker? gcc kullansaydınız?**
C: Dersin amacı yazılım yığınının alt katmanlarını anlamak. Ayrıca loader'ı kendi
toolchain'imizle derleyerek araç zincirini sistem-yazılımı seviyesinde ikinci kez kanıtladık.

---

## 11. Komut Kopya Kâğıdı (canlı demo için)

```
cd assembler_1/assembler_1

# Uygulama derle
python run_link.py apps/t1_arith_led.s -T apps/app.ld -o apps/t1_arith_led -v

# FPGA'ya yükle (COM'u kendi portunla değiştir)
cd host
python host_loader.py --port COM5 --baud 9600 --bin ../apps/t1_arith_led.bin --addr 0x3000 --entry 0x3000 -v

# Sentez öncesi doğrulama (ISS) — istersen göster
cd ..
python loader/test_loader.py
python apps/test_apps.py

# Loader'ı yeniden kurmak gerekirse (sentez gerektirir)
python loader/build_loader.py --install
```
**Ezber sayılar:** loader 328B/82 komut · CRC kontrol 0x29B1 · ACK 0x06 / NAK 0x15 ·
LED 42=0b101010 · decode mem_addr[31:28] · BRAM 16KB (loader@0x0, app@0x3000) ·
UART 0x2000_0000 · GPIO 0x1000_0000.

---

## 12. Bireysel Q&A İpuçları (RACI'ye göre)
Herkes en az kendi sorumlu (R) olduğu paketi **derinlemesine** bilmeli:
- **Fatih** → Assembler genişletme (XOR/XORI/LBU, opcode_table)
- **Senanur** → Host + CRC + paket, Test programları + demo
- **Recep Sami** → UART / SoC (Verilog)
- **Şeyma** → Loader (RV32I) + ISS doğrulama, Rapor

> Hoca bireysel soruda büyük olasılıkla "kendi modülünde küçük bir değişiklik" isteyecek
> (§9 tablosu). Herkes kendi modülünde canlı düzenleme + yeniden yükleme zincirini prova etsin.
