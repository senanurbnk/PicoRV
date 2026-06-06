# Proje 3 — PicoRV32 (RV32I) için FPGA Tabanlı Yazılımsal Bootstrap Loader

> **Bu doküman raporun kaynak metnidir.** Proje 3 kapsamında ne yapıldığını, neden
> yapıldığını, nasıl doğrulandığını ve fiziksel sonuçları uçtan uca, ayrıntılı biçimde
> anlatır. Tüm sayılar, adresler, kodlamalar repodaki gerçek artefaktlardan alınmıştır.
>
> Hedef donanım: **Sipeed Tang Nano 9K** (Gowin GW1NR-LV9QN88PC6/I5).
> Araç zinciri: **Gowin EDA Education** (sentez/P&R) + kendi Python toolchain'imiz.
> Çekirdek: **PicoRV32** (Claire Wolf, ISC lisansı).
> **Durum: Tüm sistem board üzerinde fiziksel olarak çalışır durumda doğrulandı.**

---

## 1. Yönetici Özeti

Proje 3'te, 1. projede yazdığımız assembler ve 2. projede yazdığımız linker'ın üzerine,
**sistem yazılımı seviyesinde bir bootstrap loader** inşa ettik. Loader, PicoRV32'nin
**kendi RV32I komut setiyle** yazılmış (hocanın isteği), **kendi assembler+linker'ımızla
derlenmiş** bir programdır. FPGA'nin boot bölgesinde (BRAM @ `0x0000`) durur, reset sonrası
çalışır, **UART üzerinden gelen uygulama programını** RAM'e (`0x3000`) yazar, her bloğu
**CRC-16/CCITT** ile doğrular, ACK/NAK ile akışı yönetir ve yükleme bitince uygulamanın
giriş adresine `JALR` ile atlar.

Bu, Beck'in *System Software* kitabındaki **bootstrap loader** modelinin (Şekil 3.3:
"cihazdan object kodu oku → belleğe yaz → programın başına atla") modern, somut bir
karşılığıdır: cihaz = UART, hedef = RAM `0x3000`, atlama = `JALR`.

**Tamamlanan iş kalemleri:**

| # | İş | Sonuç |
|---|----|-------|
| 1 | Assembler'a 3 yeni komut (XOR, XORI, LBU) | 20 → 23 komut |
| 2 | Host (PC) yükleyici + paket protokolü + CRC-16 | `host/` (3 modül) |
| 3 | SoC'a UART donanımı + GPIO buton girişi + 16 KB BRAM | `fpga/tangnano9k_soc/` |
| 4 | RV32I bootstrap loader (82 komut, 328 byte) | `loader/loader.s` |
| 5 | RV32I komut-set simülatörü (ISS) ile FPGA'siz doğrulama | `tools/iss.py` |
| 6 | 3 test uygulaması (artan karmaşıklık) | `apps/t1,t2,t3` |
| 7 | Tang Nano 9K üzerinde fiziksel demo | ✅ çalışıyor |

---

## 2. Temel Mimari Karar: Yazılımsal Bootstrap Loader

**Karar:** Loader, donanımsal bir Verilog FSM değil, PicoRV32 üzerinde koşan bir
**RV32I yazılım programıdır**.

**Gerekçe (rapora):**
- **Hocanın talebi:** "Loader'ı PicoRV'nin kendi komut setiyle yazacaksınız."
- **Ders modeli:** Beck, *System Software*, Bootstrap Loader (Şekil 3.3) — birebir karşılık.
- **Toolchain'i ikinci kez kanıtlar:** Loader'ın kendisi de bizim assembler+linker'ımızdan
  geçer; böylece `kaynak → assembler → object → linker → executable → BRAM` zinciri
  "sistem yazılımı" seviyesinde tekrar doğrulanmış olur.
- **"Reset modunda tutma" yorumu:** Şablondaki "FSM işlemciyi reset'te tutar, bitince
  bırakır" ifadesi bu modelde şöyle karşılanır: uygulama loader koşarken henüz başlamamıştır
  (bekler); "reset'i bırakma" = loader'ın uygulamanın giriş adresine `JALR` ile atlamasıdır.
  FSM ise loader programının iç durum makinesidir.

---

## 3. Sistem Mimarisi ve Uçtan Uca Veri Akışı

```
   PC (host)                                  Tang Nano 9K (GW1NR-9)
 ┌───────────────┐                          ┌──────────────────────────────┐
 │ uygulama.s    │                          │   PicoRV32  ◄──► Bus/Decoder  │
 │   │ assembler │                          │      ▲             │          │
 │   ▼           │                          │      │       ┌─────┴─────┐    │
 │ uygulama.bin  │                          │  16KB BRAM    GPIO   UART     │
 │   │           │                          │  ├ loader@0x0  (LED  (0x2000_ │
 │   ▼           │   USB-UART (BL702)        │  └ app  @0x3000 +buton) 0000) │
 │ host_loader.py├──────seri port──────────►│      ▲                  ▲     │
 │ (paket+CRC16) │   AA55|CMD|LEN|ADDR|      │      │                  │     │
 │               │◄─────ACK/NAK──────────────│   loader (RV32I) ◄──────┘     │
 └───────────────┘   DATA|CRC16             └──────────────────────────────┘
```

**Zaman sırası:**
1. `assembler` → `uygulama.o.json`; `linker` → flat image; `hex_emitter` → `uygulama.bin`.
2. `host_loader.py` `.bin`'i okur, word-hizalı bloklara böler, her bloğa CRC-16 ekler,
   UART'tan yollar.
3. PicoRV32 reset sonrası **boot BRAM'deki loader'dan** başlar (`PROGADDR_RESET=0x0`).
4. Loader UART'ı yoklar; paketleri alır, CRC doğrular, baytları **`0x3000+`**'e yazar;
   her WRITE bloğuna **ACK (0x06)**, hatada **NAK (0x15)** döner.
5. Host tüm bloklar bitince **START** paketi (entry=`0x3000`) yollar; loader oraya atlar.
6. Uygulama RAM'den koşar; LED/buton ile fiziksel gözlemlenir.

---

## 4. Bellek Haritası

Adres çözücü `soc_top.v` içinde `mem_addr[31:28]` (üst nibble) üzerinden çalışır.

| Bölge | Adres | Boyut | İçerik |
|-------|-------|-------|--------|
| Loader (.text) | `0x0000_0000 – 0x0000_0FFF` | 4 KB | RV32I loader; sentezde BRAM'e gömülü (`mem_init.vh`). `PROGADDR_RESET` buraya. |
| Loader stack | `0x0000_2000` | — | `STACKADDR` (loader leaf-only olduğu için pratikte kullanılmaz). |
| Uygulama | `0x0000_3000 – 0x0000_3FFF` | 4 KB | UART'tan runtime yüklenir. Entry = `0x3000`. |
| GPIO MMIO | `0x1000_0000` | — | `+0x00` LED çıkış (alt 6 bit), `+0x04` buton giriş (bit0). |
| UART MMIO | `0x2000_0000` | — | `+0x00` DATA, `+0x04` STATUS (bit0=rx_valid, bit1=tx_busy). |

| `mem_addr[31:28]` | Aygıt | Word adresi |
|-------------------|-------|-------------|
| `4'h0` | BRAM (16 KB) | `mem_addr[13:2]` (4096 word) |
| `4'h1` | GPIO | `mem_addr[3:2]` |
| `4'h2` | UART | `mem_addr[3:2]` |
| diğer | yok | `rdata=0` (CPU takılmasın) |

> **Tasarım kararı:** 2. projeden gelen SoC'da BRAM 8 KB ve decode `[31:28]` idi. Proje 3
> için BRAM **16 KB**'a çıkarıldı (`bram.v` `ADDR_BITS 11→12`) ki loader (`0x0000`) ve
> uygulama (`0x3000`) aynı fiziksel BRAM'de ayrık dursun ve loader uygulamayı yazarken
> kendini ezmesin. GPIO `0x1000_0000`'da korundu (çalışan LED pin atamaları), UART
> `0x2000_0000`'a yeni eklendi.

---

## 5. Faz 0 — Assembler Genişletmesi (XOR, XORI, LBU)

**Problem:** Loader'ın CRC-16/CCITT hesabı temelde **XOR** gerektirir; mevcut 20 komutluk
sette XOR yoktu. Ayrıca UART'tan bayt okurken işaretsiz genişletme için LBU faydalıdır.

**Çözüm:** `opcode_table.py`'a 3 komut eklendi. `encoder.py` ve `assembler.py` zaten
formata göre genel (generic) dispatch yaptığından **değişmedi** — yüzey minimum.

| Komut | Format | opcode | funct3 | funct7 | İşlev |
|-------|--------|--------|--------|--------|-------|
| XOR | R | `0110011` | `100` | `0000000` | rd = rs1 ^ rs2 |
| XORI | I | `0010011` | `100` | — | rd = rs1 ^ imm |
| LBU | I (load) | `0000011` | `100` | — | rd = zero_ext(mem[rs1+imm][7:0]) |

**Doğrulama (bilinen-doğru kodlamalar):**

| Assembly | Üretilen | Beklenen |
|----------|----------|----------|
| `XOR x1,x2,x3` | `0x003140B3` | `0x003140B3` ✓ |
| `XORI x1,x2,5` | `0x00514093` | `0x00514093` ✓ |
| `XORI x5,x6,-1` | `0xFFF34293` | `0xFFF34293` ✓ (işaret genişletme) |
| `LBU x1,0(x2)` | `0x00014083` | `0x00014083` ✓ |
| `LBU x10,4(x11)` | `0x0045C503` | `0x0045C503` ✓ |

Toplam komut: **23**. 1. ve 2. proje testleri (test1.asm, test2.asm, L1, L3, blink)
hatasız geçmeye devam etti (regresyon yok).

> Not: AUIPC eklenmedi — loader'ın tüm adresleri sabit (UART/GPIO MMIO, entry); `LUI+ADDI`
> yeterli olduğu için gereksizdi.

---

## 6. Faz 2 — Host (PC) Yükleyici, Paket Protokolü ve CRC

### 6.1 Paket Protokolü (host ↔ loader birebir aynı)

```
+-------+-----+-----+-----------+-----------+--------+
| SYNC  | CMD | LEN |   ADDR    |   DATA    | CRC16  |
| AA 55 | 1B  | 1B  |  4B (LE)  |  LEN bayt |  2B LE |
+-------+-----+-----+-----------+-----------+--------+
```

| Alan | Anlam |
|------|-------|
| SYNC | `0xAA 0x55` çerçeve başı |
| CMD | `0x01`=WRITE_BLOCK, `0x02`=START(jump), `0x03`=PING |
| LEN | DATA uzunluğu (WRITE'ta; START/PING'de 0) |
| ADDR | Hedef adres (WRITE) / entry adresi (START), little-endian |
| DATA | Ham program baytları (little-endian word düzeni) |
| CRC16 | **SYNC hariç** CMD..DATA üzerinden, little-endian gönderilir |
| Yanıt | `0x06` ACK / `0x15` NAK (START sonrası yanıt yok; loader atlar) |

Blok boyu **4'ün katı** (word hizalı) seçilir → loader veriyi `SB` ile bayt bayt yazar,
hizalama problemi olmaz.

### 6.2 CRC-16/CCITT-FALSE

| Parametre | Değer |
|-----------|-------|
| width | 16 |
| polinom | `0x1021` |
| init | `0xFFFF` |
| reflection (in/out) | **yok** (MSB-first) |
| xorout | `0x0000` |
| **check** (`"123456789"`) | **`0x29B1`** |

**Reflection'sız MSB-first** seçildi çünkü RV32I loader'da birebir yazılabilir
(sola kaydır, bit15'i test et, koşullu `XOR 0x1021`). Checksum yerine CRC seçimi:
CRC burst (ardışık bit) hatalarını çok daha güçlü yakalar — seri hat için kritik (PÇ6).

### 6.3 Host modülleri (`host/`)

| Dosya | İçerik | Doğrulama |
|-------|--------|-----------|
| `crc.py` | Bitwise + tablo CRC; ikisi de aynı | check=`0x29B1` ✓, 200 random'da tablo==bitwise ✓ |
| `packet.py` | `build_packet` / `parse_packet` / `iter_blocks` | round-trip ✓, bozuk-CRC yakalama ✓ |
| `host_loader.py` | pyserial sürücü: WRITE/START/PING, ACK/NAK, retry, timeout, `--echo-test`, `--ping`, `--selftest` | self-test ✓ |

CLI:
```bash
python host_loader.py --port COM5 --baud 9600 --bin app.bin --addr 0x3000 --entry 0x3000
python host_loader.py --port COM5 --echo-test          # Faz 1 UART bring-up
python host_loader.py --selftest                        # FPGA'siz crc+paket
```

---

## 7. Faz 1 — SoC Donanımı (UART + GPIO buton + 16 KB BRAM)

2. projenin SoC'una (PicoRV32 + BRAM + GPIO-LED) Proje 3 için eklenenler:

### 7.1 `uart.v` — Minimal 8N1 UART (yeni)
- **TX:** shift register, start(0) + 8 data (LSB-first) + stop(1). `STATUS.tx_busy` aktifken
  yazma yok sayılır (yazılım önce yoklar → bus stall yok).
- **RX:** start biti kenarı yakalanır, **orta-bit örnekleme** (DIV/2 ile merkeze gidilir),
  2-FF senkronizer ile metastabilite önlenir. Bayt hazır olunca `STATUS.rx_valid=1`,
  DATA okununca temizlenir.
- **MMIO:** `+0x00` DATA (yaz=TX, oku=RX byte + rx_valid temizle), `+0x04` STATUS.
- **Baud:** `DIV = CLK_FREQ/BAUD`. Bring-up 9600 (DIV=2812), sonra 115200 (DIV=234).

### 7.2 `gpio.v` — LED çıkış + buton giriş (genişletildi)
- `+0x00` LED (yaz: `wdata[5:0]`), `+0x04` buton (oku: bit0, 1=basılı).
- Adres ayrımı `reg_addr = mem_addr[3:2]` ile.

### 7.3 `soc_top.v` — Entegrasyon
- UART instance + `0x2` decode + top-level `uart_rx/uart_tx` portları.
- Buton: `btn_user_n` (active-low) → 2-FF senkronizer → ters çevir ("1=basılı") → `gpio.btn_in`.
- Tek-cycle yaz/oku strobe: `bus_access = mem_valid && mem_ready`.
- Okuma mux: `bram_sel ? bram_rdata : gpio_sel ? gpio_rdata : uart_sel ? uart_rdata : 0`.
- PicoRV32: RV32I-only (`PROGADDR_RESET=0x0`, mul/div/irq/compressed kapalı).

### 7.4 `bram.v` — 16 KB + araç zinciri köprüsü
- `ADDR_BITS 11→12` (8→16 KB). Per-byte write-strobe (SB için).
- **Init mekanizması:** `\`include "mem_init.vh"` (toolchain üretir). Gowin'in `$readmemh`'i
  sessizce yok saymasına karşı header-guard'lı `mem[i]=32'h...;` deyimleri (bkz. §11).

### 7.5 Pin Atamaları (`tangnano9k.cst`, board şemasından doğrulandı)

| Sinyal | Pin | IO_TYPE | Not |
|--------|-----|---------|-----|
| clk_27mhz | 52 | LVCMOS33 | dahili osilatör |
| btn_reset_n | 4 | LVCMOS18 | reset butonu (active-low) |
| btn_user_n | 3 | LVCMOS18 | T3 kullanıcı butonu (active-low) |
| led_n[0..5] | 10,11,13,14,15,16 | LVCMOS18 | active-low LED (Bank3, 1.8V) |
| uart_tx | 17 | LVCMOS33 | FPGA→PC (Bank2) |
| uart_rx | 18 | LVCMOS33 | PC→FPGA (Bank2) |

> UART pinleri (17/18) Bank2'de; MSPI flash pinleriyle **çakışmaz**. LED/buton Bank3'te
> 1.8V beslemeli olduğu için **LVCMOS18** zorunlu (aksi halde sentezde CT1136 hatası, §11).

---

## 8. Faz 3 — RV32I Bootstrap Loader (`loader/loader.s`)

**82 komut, 328 byte.** Tek dosya → cross-file relocation gerektirmez. Yalnızca
desteklenen 23-komut alt kümesi kullanılır.

### 8.1 Durum Makinesi (FSM)
```
SYNC   : 0xAA, 0x55 yakala (yoksa aramayı sürdür)
HEADER : CMD, LEN, ADDR(4B LE) oku  →  her baytı CRC'ye kat
DATA   : LEN bayt oku → [ADDR+i]'ye SB ile yaz, CRC'ye kat
CRC    : gelen CRC16'yı hesaplananla karşılaştır
  ├ eşit  → CMD=START ise JUMP, değilse ACK(0x06)
  └ değil → NAK(0x15) (host retransmit eder)
JUMP   : JALR x0, 0(s4)  → uygulamaya devret
```

### 8.2 Register Tahsisi
Kalıcı durum saklı (callee-saved) registerlarda; leaf altprogramlar yalnız `t*`/`a0`/`ra`
kullanır, **başka altprogram çağırmaz** → tek seviye `ra` yeter, **stack gerekmez**.

| Reg | Anlam | | Reg | Anlam |
|-----|-------|-|-----|-------|
| s0 | UART base (`0x2000_0000`) | | s4 | hedef/entry adresi |
| s1 | crc (çalışan) | | s5 | gelen crc |
| s2 | cmd | | s6 | sayaç i |
| s3 | len | | s7 | yazma pointer'ı |

### 8.3 Altprogramlar (leaf)
- `getc` → `a0`: `STATUS.rx_valid` yoklar, `DATA` okur, `0xFF` maskeler.
- `putc(a0)`: `STATUS.tx_busy` yoklar, `DATA`'ya yazar.
- `crc16_byte`: `s1 = CRC16_update(s1, a0)` — `host/crc.py` ile **birebir aynı algoritma**.

### 8.4 Loader Sembol Haritası (linker map'ten)
```
_start      0x0000      data_done   0x009C      putc        0x00F0
find_aa     0x0004      send_nak    0x00C8      crc16_byte  0x0104
main_loop   0x0004      do_jump     0x00D4      crc_loop    0x011C
data_loop   0x0080      getc        0x00D8      crc_skip    0x0138
                                                 .text sonu  0x0148 (328B)
```

### 8.5 BRAM'e gömme
`build_loader.py`: `loader.s → loader.o.json → loader.bin/.hex → loader_init.vh`.
`--install` ile `loader_init.vh → mem_init.vh` ve `bram.v` bunu `\`include` eder; loader
sentez zamanında bitstream'e gömülür. Uygulama gömülmez — runtime'da UART'tan gelir.

---

## 9. Doğrulama Metodolojisi — Komut-Set Simülatörü (ISS)

**Problem:** Loader'ın doğruluğunu sentez olmadan kanıtlamak. Tek yol: gerçek makine kodunu
çalıştırmak.

**Çözüm:** `tools/iss.py` — bizim linker'ımızın ürettiği RV32I makine kodunu çalıştıran
küçük bir **komut-set simülatörü**. UART ve GPIO MMIO'yu da modeller (`soc_top.v` davranışı).
Bu, "yazılımı donanımdan önce doğrula" prensibinin somutlaşmasıdır.

### 9.1 `loader/test_loader.py` — Gerçek loader.bin'i ISS'te koştur
Host (`host/packet.py`) WRITE+START paketleri üretir; ISS loader'ı çalıştırır:

| Test | Sonuç |
|------|-------|
| **load+jump** | 2 blok ACK'lendi, RAM[`0x3000`..] == gönderilen app (**byte-exact, endianness doğru**), pc → `0x3000` |
| **jump sonrası app koştu** | GPIO/LED = 42 (`0b101010`) |
| **bozuk CRC → NAK → retransmit** | İlk pakette NAK, host yeniden yolladı → ACK, RAM yine birebir |

> **Kritik kanıt:** Loader her bloğu ACK'ledi ⟹ **loader CRC'si host CRC'si ile birebir**
> (uyuşmasaydı her blok NAK olurdu). Endianness ISS'te RAM karşılaştırmasıyla doğrulandı —
> bu projenin 1 numaralı hata kaynağı sentezden önce elendi.

### 9.2 `fpga/tangnano9k_soc/uart_echo_test/uart_model_test.py` — UART FSM cycle-model
`uart.v` TX/RX durum makinelerinin Python ikizi; loopback'te `0x00/0xFF/0xAA/0x55` dahil
tüm bayt desenleri birebir geri geldi. Bit-zamanlaması (shift yönü, 8N1, orta-bit örnekleme)
sentezden önce kanıtlandı (iverilog/verilator olmadan).

### 9.3 `apps/test_apps.py` — 3 uygulama ISS'te
T1/T2/T3 `app.ld`(@`0x3000`) ile derlenip ISS'te koşturuldu (sonuçlar §10).

---

## 10. Test Uygulamaları (en az 3, artan karmaşıklık)

| Test | Dosya | Boyut | İçerik | Test ettiği | ISS sonucu |
|------|-------|-------|--------|-------------|-----------|
| T1 | `t1_arith_led.s` | 24B / 6 komut | 40+2=42 → LED | en basit yükleme kanıtı | LED=`0b101010` ✓ |
| T2 | `t2_loop_blink.s` | 36B / 9 komut | 6-bit sayaç + gecikme | döngü, BNE/J, zamanlama | sayaç monoton [0,1,2,…] ✓ |
| T3 | `t3_func_button.s` | 44B / 11 komut | `get_button()` (JAL/RET) + butona göre LED | fonksiyon çağrısı, PC-bağıl, **GPIO girişi** | buton=0→`0b001001`, buton=1→`0b111111` ✓ |

Her biri loader'ın UART üzerinden yüklediği gerçek uygulamadır; üçü birlikte JAL/JALR,
branch, bellek erişimi, MMIO çıkış ve MMIO giriş yollarını kapsar.

---

## 11. Karşılaşılan Sorunlar ve Çözümler

Proje boyunca öğretici sorunlar çıktı; her biri raporun "Karşılaşılan Problemler"
bölümü için zengin malzemedir.

1. **Komut seti eksiği (XOR yok) — CRC yazılamıyor.** CRC-16 temelde XOR'dur. Çözüm:
   assembler'a XOR/XORI/LBU eklendi (relocation mantığına dokunmadan). Ders: araç zincirini
   uygulamanın ihtiyacına göre genişletmek.
2. **Adres decode çakışması.** Planın `0x02/0x03` MMIO adresleri `[31:28]` decode'da BRAM'e
   düşüyordu. Çözüm: GPIO `0x1`, UART `0x2`, BRAM 16 KB; çalışan SoC bozulmadı.
3. **Endianness riski.** PicoRV32 little-endian; host bayt sırası ile loader `SB` yazımı
   uyuşmazsa program çöp olur. Çözüm: ISS'te RAM geri-okuma ile sentezden ÖNCE doğrulandı.
4. **`$readmemh` Gowin'de sessizce yok sayılıyor.** BRAM sıfır kalıyor, CPU NOP koşuyor.
   Çözüm: toolchain `mem_init.vh` (explicit `mem[i]=32'h...;`) üretiyor, `bram.v` `\`include`
   ediyor — preprocessor seviyesinde garanti.
5. **`.vh` standalone derlenince syntax hatası (EX3863).** Gowin `.vh`'yi modül gibi parse
   ediyor. Çözüm: header-guard (`\`ifdef BRAM_INIT_LOAD`) — C'deki `#ifndef` deseninin
   Verilog karşılığı.
6. **Bank vccio çakışması (CT1136).** LED/buton Bank3'te 1.8V; LVCMOS33 ile çakışıyor.
   Çözüm: LVCMOS18.
7. **Loop unroll limiti (EX3934).** BRAM sıfırlama for-loop'u Gowin'in 2000 unroll limitini
   aşıyordu. Çözüm: explicit sıfırlama kaldırıldı (inferred BSRAM zaten 0).
8. **İki kopya `src/` tuzağı.** Gowin proje kendi `fpga_project/src/` kopyasını kullanır;
   kök dosyalar güncellenince `src/`'e senkronlamak gerekti.
9. **Buton pin belirsizliği.** Kaynaklar S1/S2 ↔ pin3/pin4 eşleşmesinde tutarsızdı; reset
   pin4'te çalıştığından kullanıcı butonu pin3'e konuldu — board'da doğrulandı.

---

## 12. Fiziksel Demo (Tang Nano 9K) — Doğrulandı ✅

`docs/fpga_runbook.md`'deki adımlar board üzerinde uygulandı ve **tüm sistem çalıştı**:

1. **Echo bring-up:** `host_loader.py --echo-test` → 256 baytın tamamı birebir geri geldi
   (UART RX+TX + MMIO + CPU'nun BRAM'den koşması fiziksel kanıtlandı).
2. **Loader kuruldu** (`build_loader.py --install`), sentezlendi, board'a yüklendi.
3. **T1/T2/T3 UART'tan yüklendi ve çalıştı:** T1 LED=42, T2 LED sayaç animasyonu,
   T3 butona basınca 6 LED / bırakınca desen.
4. NAK/retransmit ve kararlı ardışık yükleme gözlemlendi.

---

## 13. Dosya Envanteri (Proje 3'te eklenen/değişen)

```
assembler_1/assembler_1/
├─ opcode_table.py          [değişti] XOR/XORI/LBU
├─ host/                    [YENİ]
│  ├─ crc.py                CRC-16/CCITT-FALSE (bitwise+tablo)
│  ├─ packet.py             paket çerçeveleme + parse
│  ├─ host_loader.py        pyserial yükleyici (WRITE/START/PING/echo-test)
│  └─ requirements.txt      pyserial
├─ loader/                  [YENİ]
│  ├─ loader.s              RV32I bootstrap loader (82 komut, 328B)
│  ├─ loader.ld             linker script @0x0000
│  ├─ build_loader.py       loader → mem_init.vh
│  └─ test_loader.py        ISS doğrulama harness'i
├─ apps/                    [YENİ]
│  ├─ t1_arith_led.s / t2_loop_blink.s / t3_func_button.s
│  ├─ app.ld               @0x3000
│  └─ test_apps.py          ISS doğrulama
├─ tools/
│  └─ iss.py                [YENİ] RV32I komut-set simülatörü + MMIO
├─ fpga/tangnano9k_soc/
│  ├─ uart.v                [YENİ] 8N1 UART
│  ├─ gpio.v                [değişti] buton girişi
│  ├─ soc_top.v             [değişti] UART + buton + 16KB
│  ├─ bram.v                [değişti] 16KB + mem_init.vh
│  ├─ tangnano9k.cst        [değişti] UART + buton pinleri
│  └─ uart_echo_test/       [YENİ] echo bring-up + uart_model_test.py
└─ docs/
   ├─ proje3_plan.md        reconcile edilmiş plan
   ├─ memory_map.md         bellek haritası
   ├─ fpga_runbook.md       board adımları
   └─ PROJE3.md             bu dosya
```

---

## 14. Komut Referansı (yeniden üretmek için)

```bash
cd assembler_1/assembler_1

# Loader'ı derle + SoC'a kur
python loader/build_loader.py --install

# Uygulamaları derle
python run_link.py apps/t1_arith_led.s  -T apps/app.ld -o apps/t1_arith_led
python run_link.py apps/t2_loop_blink.s -T apps/app.ld -o apps/t2_loop_blink
python run_link.py apps/t3_func_button.s -T apps/app.ld -o apps/t3_func_button

# FPGA'siz doğrulama (hepsi yeşil)
python host/crc.py
python host/packet.py
python loader/test_loader.py
python apps/test_apps.py
python fpga/tangnano9k_soc/uart_echo_test/uart_model_test.py

# Board'a yükle (board bağlıyken)
python host/host_loader.py --port COM5 --baud 9600 --bin apps/t1_arith_led.bin \
                           --addr 0x3000 --entry 0x3000
```

---

## 15. Program Çıktıları (PÇ) Eşlemesi — Rapora

> Rapor metninde PÇ'ler ayrı başlık değil, ilgili cümlenin sonunda parantez içinde verilir.

| PÇ | Nerede karşılanır |
|----|-------------------|
| **PÇ1** (Loader Doğruluğu + FPGA Çalışma) | §8 loader, §9 ISS doğrulaması, §12 fiziksel demo. Loader tüm relocation/CRC/yükleme/jump'ı doğru yapıyor; board'da stabil. |
| **PÇ6** (Literatür + Yöntem) | §2 (Beck bootstrap modeli), §6.2 (checksum vs CRC, CRC-16/CCITT seçimi), §9 (ISS ile yazılım-önce doğrulama yöntemi gerekçesi). |
| **PÇ7** (Test + Analiz) | §9 doğrulama matrisi, §10 üç test uygulaması, §11 sorun analizi, yükleme süresi metriği (115200 ile ~12×). |
| **PÇ8** (Sürdürülebilirlik) | Açık ISA (RISC-V) + açık toolchain; eğitsel/ekonomik etki; CRC'li güvenilir loader'ın kritik sistemlerdeki önemi; OTA güncellenebilirlik (e-atık azaltma). |
| **PÇ12/PÇ13** (Takım + Rapor/Sunum) | Görev dağılımı tablosu, git akışı, bireysel canlı düzenleme provası (§14 tek-komut zinciri). |

---

## 16. Toplanacak Metrikler (rapor §3.2 için board'dan)

- **Kod boyutları:** loader 328B/82 komut; echo 44B; T1 24B, T2 36B, T3 44B.
- **Yükleme süresi vs boyut:** `host_loader.py -v` zaman damgası. Gerçek ölçümler **9600 baud**
  için verilir. Teorik: süre ≈ (toplam_bayt × 10 bit) / baud + ACK gecikmesi.
  - **115200 NOTU:** Baud, FPGA'da sentez zamanında sabit bir parametredir (soc_top.v `UART_BAUD`,
    uart.v `DIV=CLK_FREQ/BAUD`). Mevcut bitstream 9600'e göre üretildiği için host'u tek başına
    115200 yapmak hız uyumsuzluğu → ACK yok → yükleme tamamlanamaz. 115200 ölçümü için
    `UART_BAUD=115200` yapıp **yeniden sentez + bitstream yükleme** gerekir. Bu nedenle rapor
    ölçümleri 9600'dedir. (Raporda Tablo 3.3 altına bu not eklendi.)
- **FPGA kaynak kullanımı:** Gowin sentez+P&R raporundan LUT / FF / BSRAM (GW1NR-9:
  ~8640 LUT4, ~6480 FF, ~468 Kbit BSRAM). Gerçek yüzdeleri Gowin raporundan al.

---

## 17. Sonuç

Proje 3'te, kendi araç zincirimizle derlenen, PicoRV32'nin kendi komut setiyle yazılmış bir
**yazılımsal bootstrap loader** geliştirdik; bunu UART tabanlı, CRC-16 doğrulamalı bir paket
protokolü ve PC tarafı bir yükleyici ile tamamladık; SoC'a UART ve buton girişi ekledik; ve
tüm bu yazılımı **sentezden önce bir komut-set simülatöründe gerçek makine kodunu çalıştırarak**
doğruladıktan sonra **Tang Nano 9K üzerinde fiziksel olarak çalıştırdık.** Böylece
`kaynak → assembler → linker → loader → UART → RAM → çalışan uygulama` zinciri uçtan uca,
fiziksel donanımda kapatılmış oldu.
