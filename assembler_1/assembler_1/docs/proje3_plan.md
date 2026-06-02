# Proje 3 — Repoya Oturtulmuş Uygulama Planı
## PicoRV32 FPGA Tabanlı Yazılımsal Bootstrap Loader

> Bu doküman, kullanıcının verdiği üst-seviye Proje 3 planının **bu repoya göre
> doğrulanmış ve düzeltilmiş** halidir. Üst-seviye gerekçeler/PÇ eşlemeleri/rapor
> yapısı için orijinal plan geçerlidir; burada **repo-gerçeği + sapmalar + kilitli
> kararlar + faz planı (gerçek dosya yollarıyla)** vardır.
>
> Temel karar: **Yazılımsal bootstrap loader** — PicoRV32 üzerinde koşan, kendi
> assembler+linker'ımızla derlenen RV32I programı. (Donanımsal FSM B-planı yedekte.)
> **Hocaya teyit edilecek** (orijinal plan §0).

---

## 1. Repo-Gerçeği (kodlamadan önce sabit kabul edilenler)

### 1.1 Dizin yapısı — plan ≠ repo
Plan `asm/ host/ loader/ rtl/` kökünde varsayıyor. **Gerçekte her şey
`assembler_1/assembler_1/` altında.** Yeni dizinler de oraya:

```
assembler_1/assembler_1/
├─ (toolchain — mevcut)  opcode_table.py, symbol_table.py, register_table.py,
│   parser.py, encoder.py, bit_layout.py, assembler.py, object_format.py,
│   linker.py, linker_script.py, hex_emitter.py, run_link.py
├─ fpga/tangnano9k_soc/   soc_top.v, bram.v, gpio.v, tangnano9k.cst/.sdc  (mevcut)
│                         + uart.v        ← YENİ
│                         + loader_init.vh      ← YENİ (üretilir)
├─ firmware/blink/         (mevcut referans demo)
├─ vendor/picorv32/        picorv32.v (ISC)     (mevcut)
├─ loader/                 ← YENİ   loader.s, loader.ld, build_loader.(sh|py)
├─ host/                   ← YENİ   host_loader.py, packet.py, crc.py
├─ apps/ (plan'da tests/)  ← YENİ   t1_arith_led.s, t2_loop_blink.s, t3_func_button.s
│                                   + app.ld
├─ tests/link/             (mevcut L1/L3 regresyon — korunur)
└─ docs/                   ← YENİ   proje3_plan.md (bu dosya), memory_map.md
```

### 1.2 Mevcut komut seti (opcode_table.py — DOĞRULANDI)
20 komut: `ADD SUB AND OR SLT | ADDI ANDI SLLI SRLI LW LB JALR ECALL | SW SB |
BEQ BNE BLT | LUI | JAL`.
Pseudo: `NOP MV LI NEG J JR RET CALL BEQZ BNEZ`.
**Yok:** XOR, XORI, ORI, LBU, AUIPC, SLT-immediate, SRAI, vb.

### 1.3 SoC bus + adres decode (soc_top.v — DOĞRULANDI)
- PicoRV32 native bus: `mem_valid, mem_ready, mem_addr, mem_wdata, mem_wstrb[3:0], mem_rdata`.
- Decode **`mem_addr[31:28]`**: `4'h0→BRAM`, `4'h1→GPIO`, diğer→`rdata=0`.
- `mem_ready`: 1-cycle toggle strobe (`ready_d <= mem_valid && !ready_d`).
- BRAM: `bram.v`, ADDR_BITS=11 (8 KB), per-byte wstrb, senkron okuma, init `loader_init.vh` `\`include` + `$readmemh` yedek.
- GPIO: `0x10000000`, alt 6 bit → LED, `led_n = ~led_value` (active-low).
- PicoRV32 param: `PROGADDR_RESET=0x0`, `STACKADDR=0x2000`, RV32I-only (mul/div/irq/compressed kapalı).
- LED .cst: clk=52, btn=4, led_n[0..5]={10,11,13,14,15,16}, **LVCMOS18** (Bank3 1.8V — CT1136 dersi).

### 1.4 Toolchain çıktı mekanizması (run_link.py / hex_emitter.py — DOĞRULANDI)
`run_link.py kaynak... -T script.ld -o base` → `base.bin`, `base.hex`, `base_init.vh`, `base.map.txt`.
`_init.vh` = `\`ifdef BRAM_INIT_LOAD ... mem[i]=32'h...; ... \`endif` (header-guard'lı).
**Bu mekanizma loader'ı BRAM'e gömmek için aynen kullanılacak.**

---

## 2. Sapmalar ve Düzeltmeler (plan varsayımı → repo gerçeği)

| # | Plan varsayımı | Repo gerçeği | Düzeltme |
|---|----------------|--------------|----------|
| 1 | loader `auipc, lbu` kullanır; CRC-16/CCITT | XOR/XORI/LBU/AUIPC **yok** | **XOR, XORI, LBU ekle** (opcode_table+encoder, 3 satır). AUIPC gereksiz (LUI+ADDI). |
| 2 | UART@0x02000000, GPIO@0x03000000, app@0x3000 | decode `[31:28]`; 0x0/0x02/0x03 hep BRAM'e düşer | GPIO **0x10000000** (sabit), UART **0x20000000**, BRAM 16KB'a (ADDR_BITS=12), loader@0x0000, app@0x3000 |
| 3 | `asm/ host/ loader/ rtl/` kök dizinleri | her şey `assembler_1/assembler_1/` altında | yeni dizinleri oraya aç |
| 4 | UART pinleri "kart kılavuzundan" | .cst'de UART pini yok | Sipeed şemasından **doğrula**, .cst'ye ekle (MSPI çakışmasını kontrol et) |
| 5 | loader relocation riski (B/J) | loader tek dosya, cross-file yok | loader relocation gerektirmez; risk yalnız yüklenen app'lerde |
| 6 | STACKADDR=0x0F00 | mevcut 0x2000 | loader stack'i loader kod bölgesini ezmemeli → §3 layout'a göre seç |

---

## 3. Reconcile Edilmiş Bellek Haritası (16 KB BRAM)

> Detay: `docs/memory_map.md`. Karar: BRAM 8 KB → 16 KB (ADDR_BITS=12). GW1NR-9'da
> BSRAM bol (26 blok); maliyet önemsiz. Bu, plan'ın 0x3000 app adresini korur.

| Bölge | Adres | Boyut | İçerik |
|-------|-------|-------|--------|
| Loader (.text) | `0x0000_0000–0x0000_0FFF` | 4 KB | RV32I loader; `loader_init.vh` ile sentezde gömülü. PROGADDR_RESET buraya. |
| Loader stack | `0x0000_2000` (aşağı doğru) | — | STACKADDR; app bölgesinin altında, güvenli. |
| Uygulama | `0x0000_3000–0x0000_3FFF` | 4 KB | UART'tan yüklenen .text+.data. Entry = 0x3000. |
| GPIO MMIO | `0x1000_0000` | — | alt 6 bit → LED (mevcut, değişmez). |
| UART MMIO | `0x2000_0000` blok | — | RX/TX/STATUS (aşağıda). |

Decode: `[31:28]` → `0x0`=BRAM(16KB), `0x1`=GPIO, `0x2`=UART, diğer=0.
**Not:** loader 0x0000-0x0FFF; app yazımı 0x3000+; çakışma yok. BRAM word-addr = `mem_addr[13:2]`.

### UART MMIO register (simpleuart tarzı)
| Offset | İsim | Erişim | Açıklama |
|--------|------|--------|----------|
| +0x00 | UART_DATA | R/W | Oku: gelen bayt (bit[7:0]); Yaz: gönderilecek bayt |
| +0x04 | UART_STATUS | R | bit0=rx_valid, bit1=tx_busy |
| +0x08 | UART_DIV | R/W | (ops.) baud bölücü; sabit de olur |

> Byte okuma: `LW` ile UART_DATA oku + `ANDI rd, rd, 0xFF` maskele (LBU eklersek `LBU` da olur).

---

## 4. Paket Protokolü (host ↔ loader birebir) — plan §4.5 aynen

```
SYNC(AA 55) | CMD(1) | LEN(1) | ADDR(4 LE) | DATA(LEN) | CRC16(2)
CMD: 0x01=WRITE_BLOCK  0x02=START(jump)  0x03=PING
CRC16: CRC-16/CCITT (poly 0x1021), SYNC hariç CMD..DATA üzerinden
Yanıt: 0x06=ACK / 0x15=NAK
Blok boyu 4'ün katı (word hizalı) → loader SW ile yazar, basitleşir.
```

---

## 5. Faz Planı (gerçek repo yollarıyla, faz-sonu kriteriyle)

> Çalışma dizini hep: `assembler_1/assembler_1/`

**Faz 0 — Hazırlık + toolchain genişletme (½ gün)**
- `assembler`a **XOR, XORI, LBU** ekle (opcode_table.py + encoder.py); küçük birim testle encode'u doğrula; L1/L3 + blink regresyonu bozulmadı.
- `host/`, `loader/`, `apps/` dizinlerini aç. `pyserial` kur.
- ✅ Kriter: yeni komutlar doğru encode; mevcut testler yeşil; blink hâlâ derleniyor.

**Faz 1 — UART loopback (donanım) (½–1 gün)**
- `fpga/tangnano9k_soc/uart.v` ekle (picosoc kaynaklı, ISC). soc_top.v'ye UART instance + `0x2` decode + top-level `uart_rx/uart_tx` portları. .cst'ye **doğrulanmış** UART pinleri.
- Geçici echo firmware'i (BRAM'e gömülü) ile baytı geri yolla.
- ✅ Kriter: `host_loader.py --ping` → echo geri geliyor; baud doğru (önce **9600**).

**Faz 2 — Host protokol + CRC (FPGA'siz) (½ gün)**
- `host/crc.py` (CRC-16/CCITT, bilinen vektörle birim test), `host/packet.py` (encode/decode round-trip), `host/host_loader.py` (pyserial, ACK/NAK/retry/timeout).
- ✅ Kriter: CRC vektörleri geçer; paket encode→decode kayıpsız.

**Faz 3 — Loader v1: tek blok + geri-okuma (1–1.5 gün)**
- `loader/loader.s`: IDLE→SYNC→HEADER→DATA→CRC→ACK/NAK; RAM'e yaz; **JUMP yok**, yazdığını geri okuyup host'a yolla (endianness doğrulaması). `loader.ld` (@0x0000). `build_loader` → `loader_init.vh` → sentez.
- ✅ Kriter: 1 blok → ACK; geri-okunan = gönderilen (endianness DOĞRULANDI).

**Faz 4 — Loader v2: çoklu blok + START/JUMP (1 gün)**
- Tüm `out.bin`'i bloklarla yükle; START → entry'ye `jalr`. En basit app: T1.
- ✅ Kriter: `host_loader.py app.bin` → birkaç sn → T1 LED'i fiziksel yanıyor.

**Faz 5 — Tüm testler + sağlamlık (1 gün)**
- T2, T3. Kasıtlı bozuk CRC → NAK→retransmit. 115200 baud'a çık. 10 ardışık yükleme %100.
- ✅ Kriter: 3 test çalışıyor; hata enjeksiyonunda loader kilitlenmeden toparlıyor.

**Faz 6 — Metrik + rapor + video (1.5 gün)**
- Yükleme süresi vs boyut (tools/measure_load_time.py); Gowin kaynak raporu. Rapor (orijinal plan §9). Video (≤5 dk).
- ✅ Kriter: teslim paketi hazır (07.06.2026 23:59).

---

## 6. Test Programları (yalnız desteklenen alt küme!)
| Test | Dosya | İçerik | Sınar |
|------|-------|--------|-------|
| T1 | `apps/t1_arith_led.s` | aritmetik → LED'e SW | loader doğru yükledi mi |
| T2 | `apps/t2_loop_blink.s` | delay döngüsü + blink (beq/bne) | döngü, dallanma, zamanlama |
| T3 | `apps/t3_func_button.s` | jal/jalr alt program + buton (GPIO read) | fonksiyon çağrısı, PC-bağıl, GPIO girişi |

> T3 için GPIO'ya **okuma/buton girişi** gerekebilir — mevcut gpio.v yalnız LED çıkışı.
> Buton girişi gerekiyorsa gpio.v genişletilecek (ayrı offset, read-only buton reg).

---

## 7. Kilitlenecek Kararlar (kodlamadan önce)
- [ ] Loader mimarisi: yazılımsal bootstrap (öneri) — **hocaya teyit**
- [ ] Komut seti: XOR+XORI+LBU ekle (öneri) vs emüle et
- [ ] Bellek: 16 KB BRAM, app@0x3000, GPIO@0x10000000, UART@0x20000000 (öneri)
- [ ] UART pinleri Sipeed şemasından doğrulandı (MSPI çakışması yok), baud önce 9600
- [ ] T3 buton girişi için gpio.v genişletmesi gerekli mi
- [ ] Video dosya adı PROJE3, teslim 07.06 teyitli

---
*Kaynak: kullanıcının BIL302 Proje 3 planı + bu reponun doğrulanmış durumu (HEAD 42c5ccc).*
