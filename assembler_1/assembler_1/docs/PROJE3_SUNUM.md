# Proje 3 — Ne Yaptık? (Kod Üzerinden Detaylı Anlatım)

> Bu doküman **yalnızca Proje 3 kapsamında yazdığımız kodu** anlatır: hangi dosya,
> ne işe yarıyor, içinde ne var (gerçek kod parçalarıyla). Proje 1 (assembler) ve
> Proje 2 (linker) altyapısının **üzerine** eklediklerimize odaklanır.
>
> **Git'ten Proje 3'ün fazları** (commit sırası):
> | Commit | Faz | İçerik |
> |---|---|---|
> | `e054e33` | Faz 0+2 | Assembler genişletme (XOR/XORI/LBU) + host (crc/packet/host_loader) |
> | `461fe6c` | Faz 1 | UART donanımı (uart.v) + SoC entegrasyonu + echo bring-up |
> | `d7ecfa5` | Faz 3/4 | RV32I bootstrap loader + ISS doğrulama |
> | `cc470e9` | Faz 5 | T2/T3 uygulamaları + GPIO buton girişi |

---

## 0. Proje 3 Nedir? Neyi Miras Aldık, Neyi Ekledik?

**Miras (P1+P2'den, hazır):** assembler (`parser`, `opcode_table`, `encoder`, `symbol_table`,
`bit_layout`, `assembler.py`), linker (`object_format`, `linker.py`, `linker_script`),
`hex_emitter`, `run_link`. Bunlar koddan `.bin` üretiyordu.

**Proje 3'te EKLEDİĞİMİZ yeni şeyler:**
1. **Assembler'a 3 komut** (XOR, XORI, LBU) — loader'ın CRC'yi yazabilmesi için.
2. **Host tarafı** (`host/`): CRC-16, paket protokolü, seri yükleyici.
3. **UART donanımı** (`uart.v`) + SoC'a entegrasyon + GPIO'ya buton girişi + BRAM 16 KB.
4. **Bootstrap loader** (`loader/loader.s`) — PicoRV'nin kendi diliyle yazılan sistem yazılımı.
5. **ISS** (`tools/iss.py`) — sentezden önce gerçek makine kodunu çalıştıran simülatör.
6. **3 test uygulaması** (`apps/`) + echo bring-up firmware'i.

Aşağıda her birini, kodunu göstererek anlatıyorum.

---

## 1. Faz 0 — Assembler'a 3 Komut Ekleme
**Dosya:** `opcode_table.py`

**Neden?** Loader'ın CRC-16 hesabı **XOR** gerektirir; mevcut 20 komutluk sette XOR yoktu.
UART'tan bayt okumak için de işaretsiz `LBU` faydalı. Çözüm tablo seviyesinde, **3 satır**:

```python
# R-tipi (rd = rs1 ^ rs2)
self._add(OpcodeEntry("XOR",  "R", R, funct3=0b100, funct7=0b0000000, description="rd = rs1 ^ rs2"))
# I-tipi (rd = rs1 ^ imm)
self._add(OpcodeEntry("XORI", "I", IA, funct3=0b100, description="rd = rs1 ^ imm"))
# I-tipi yük (rd = zero_ext(mem[rs1+imm][7:0]))
self._add(OpcodeEntry("LBU",  "I", IL, funct3=0b100, description="rd = zero_ext(mem[rs1+imm][7:0])"))
```

**Önemli:** `encoder.py` ve `assembler.py` **hiç değişmedi**. Çünkü encoder formata göre
genel çalışıyor: XOR R-tipi → standart R encoder; XORI/LBU I-tipi → standart I encoder.
Bu da tasarımın temiz olduğunu gösterir (yeni komut = sadece tabloya satır). Komut sayısı
**20 → 23** oldu.

---

## 2. Faz 2 — Host (PC) Tarafı
**Klasör:** `host/` — `crc.py`, `packet.py`, `host_loader.py`

### 2.1 `host/crc.py` — CRC-16/CCITT-FALSE

```python
POLY = 0x1021
INIT = 0xFFFF

def crc16_ccitt(data: bytes, init: int = INIT) -> int:
    crc = init & 0xFFFF
    for b in data:
        crc ^= (b << 8) & 0xFFFF          # baytı üst 8 bite XOR'la
        for _ in range(8):                 # 8 bit işle
            if crc & 0x8000:               # en yüksek bit 1 ise
                crc = ((crc << 1) ^ POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF
```

**Ne yapar?** Paketin "parmak izini" üretir. Bir bit bozulsa bile CRC değişir → alıcı
bozulmayı yakalar. **Neden bu varyant (yansımasız, MSB-first)?** Çünkü loader bunu RV32I'da
**birebir** yazabilsin (sola kaydır → bit15 test → koşullu `XOR 0x1021`). Doğrulama: kodda bir
self-test var, `crc16_ccitt(b"123456789") == 0x29B1` (standart kontrol değeri).

### 2.2 `host/packet.py` — Paket Çerçeveleme

```python
SYNC0, SYNC1 = 0xAA, 0x55
CMD_WRITE_BLOCK, CMD_START, CMD_PING = 0x01, 0x02, 0x03
ACK, NAK = 0x06, 0x15

def build_packet(cmd, addr=0, data=b""):
    # gövde = CMD | LEN | ADDR(4 LE) | DATA   (CRC bunun üzerinden hesaplanır)
    body = bytes([cmd & 0xFF, len(data) & 0xFF]) + struct.pack("<I", addr & 0xFFFFFFFF) + data
    crc = crc16_ccitt(body)
    return bytes([SYNC0, SYNC1]) + body + struct.pack("<H", crc)   # SYNC + gövde + CRC(2 LE)
```

**Ne yapar?** `SYNC(AA55) | CMD | LEN | ADDR | DATA | CRC16` çerçevesini kurar. `<I` = 4 bayt
little-endian adres, `<H` = 2 bayt little-endian CRC. CRC **SYNC hariç** gövde üzerinden.
Ayrıca `iter_blocks()` `.bin`'i 4'ün katı bloklara böler (word hizalı → loader `SB` ile yazar).

### 2.3 `host/host_loader.py` — Seri Yükleyici (pyserial)

```python
def send_block(ser, addr, data, retries, timeout, verbose=False):
    pkt = build_packet(CMD_WRITE_BLOCK, addr, data)
    for attempt in range(1, retries + 1):
        ser.write(pkt)                       # paketi UART'tan yolla
        resp = _wait_ack(ser, timeout)        # tek bayt yanıt bekle
        if resp == ACK:                       # 0x06 -> başarılı
            return True
        # NAK (0x15) veya timeout -> aynı paketi YENİDEN gönder
    return False
```

**Ne yapar?** `.bin`'i bloklara böler, her bloğu WRITE paketiyle gönderir, **ACK** bekler,
gelmezse **yeniden gönderir** (güvenilir aktarım). Tüm bloklar bitince `START` paketi yollar
(loader uygulamaya atlar). CLI: `--port COM5 --baud 9600 --bin app.bin --addr 0x3000 --entry 0x3000`.
Ayrıca `--echo-test` (Faz 1 bring-up) ve `--selftest` (FPGA'sız crc+paket testi) modları var.

---

## 3. Faz 1 — UART Donanımı ve SoC Entegrasyonu
**Klasör:** `fpga/tangnano9k_soc/` — `uart.v` (YENİ), `soc_top.v` / `bram.v` / `gpio.v` / `.cst` (GÜNCELLENDİ)

### 3.1 `uart.v` — 8N1 UART (YENİ modül)

**TX (gönderim) — kaydırmalı yazmaç:**
```verilog
// {stop=1, data[7:0], start=0}, tx_shift[0] hatta verilir
assign tx = tx_active ? tx_shift[0] : 1'b1;     // boştayken hat 1
// wr_data gelince yükle:
tx_shift  <= {1'b1, wdata[7:0], 1'b0};          // start biti en başta
tx_bitcnt <= 4'd10;                              // 1 start + 8 veri + 1 stop
// her baud periyodunda 1 bit kaydır (sağa)
tx_shift <= {1'b1, tx_shift[9:1]};
```

**RX (alım) — orta-bit örnekleme + 2-FF senkronizer:**
```verilog
reg rx_q, rx_qq;
always @(posedge clk) begin rx_q <= rx; rx_qq <= rx_q; end   // metastabilite önleme
// start biti (hat 0) yakalanınca yarım bit bekle (start merkezi):
rx_div <= DIV2[15:0] - 16'd1;
// sonra her bit merkezinde örnekle (LSB-first):
rx_shift <= {rx_qq, rx_shift[7:1]};
// 8 bit toplanınca:
rx_data  <= rx_shift;  rx_valid <= 1'b1;
```

**MMIO register (CPU bununla konuşur):**
```verilog
REG_DATA:   rdata = {24'b0, rx_data};               // +0: oku=gelen bayt
REG_STATUS: rdata = {30'b0, tx_busy, rx_valid};     // +4: bit0=rx_valid, bit1=tx_busy
```
**Ne yapar?** Seri biti bayta (RX) ve baytı seri bite (TX) çevirir. `DIV = CLK_FREQ/BAUD`
(27 MHz / 9600). Yazılım önce `STATUS`'u yoklar, sonra `DATA`'ya erişir → bus stall yok.

### 3.2 `soc_top.v` — UART'ı sisteme bağlama (GÜNCELLENDİ)

**Adres çözücü (UART için `0x2` eklendi):**
```verilog
wire bram_sel = (mem_addr[31:28] == 4'h0);   // 0x0... -> BRAM
wire gpio_sel = (mem_addr[31:28] == 4'h1);   // 0x1... -> GPIO
wire uart_sel = (mem_addr[31:28] == 4'h2);   // 0x2... -> UART (YENİ)
```

**UART örneği + tek-cycle yaz/oku strobe'u:**
```verilog
wire bus_access = mem_valid && mem_ready;            // transaction tamamlandığı cycle
wire uart_wr = uart_sel && bus_access &&  (|mem_wstrb);
wire uart_rd = uart_sel && bus_access && ~(|mem_wstrb);
uart #(.CLK_FREQ(27_000_000), .BAUD(UART_BAUD)) u_uart (
    .clk(clk_27mhz), .resetn(resetn),
    .wr_en(uart_wr), .rd_en(uart_rd),
    .reg_addr(mem_addr[3:2]), .wdata(mem_wdata),
    .rdata(uart_rdata), .rx(uart_rx), .tx(uart_tx)
);
```

**Okuma mux'una UART eklendi:**
```verilog
assign mem_rdata = bram_sel ? bram_rdata
                 : gpio_sel ? gpio_rdata
                 : uart_sel ? uart_rdata          // YENİ
                 : 32'h0000_0000;
```

### 3.3 `bram.v` — 8 KB → 16 KB + `mem_init.vh` köprüsü (GÜNCELLENDİ)

```verilog
module bram #( parameter ADDR_BITS = 12, ... )       // 11->12: 8KB -> 16KB
...
initial begin
    `define BRAM_INIT_LOAD
    `include "mem_init.vh"      // toolchain'in ürettiği mem[i]=32'h...; satırları
    `undef BRAM_INIT_LOAD
    $readmemh(INIT_FILE, mem);  // yedek (Gowin bunu yok sayıyor)
end
```
**Neden 16 KB?** loader (0x0000) ve uygulama (0x3000) aynı bellekte ayrık dursun, loader
uygulamayı yazarken kendini ezmesin. **mem_init.vh:** §6'da anlatılan kritik köprü.

### 3.4 `gpio.v` — Buton girişi eklendi (GÜNCELLENDİ)

```verilog
// reg_addr=0 (+0): LED yaz ;  reg_addr=1 (+4): buton oku
always @(*) case (reg_addr)
    2'd0: rdata = {{(32-LED_COUNT){1'b0}}, led_value};   // LED durumu
    2'd1: rdata = {{(32-BTN_COUNT){1'b0}}, btn_in};      // buton (1=basılı)  YENİ
endcase
```
`soc_top.v` butonu 2-FF senkronize edip tersliyor (active-low → "1=basılı"):
```verilog
reg btn_s0, btn_s1;
always @(posedge clk_27mhz) begin btn_s0 <= btn_user_n; btn_s1 <= btn_s0; end
wire btn_pressed = ~btn_s1;
```
`.cst`'ye `uart_tx=17`, `uart_rx=18`, `btn_user_n=3` pinleri eklendi.

### 3.5 Echo bring-up (`uart_echo_test/echo.s`)
UART donanımını sentez sonrası fiziksel doğrulamak için yazdığımız küçük firmware: UART'tan
geleni aynen geri yansıtır. `host_loader.py --echo-test` 256 baytın (0x00..0xFF) geri geldiğini
doğrular. (Ayrıca `uart_model_test.py` = uart.v FSM'inin Python ikizi, sentez öncesi bit
zamanlamasını doğrular.)

---

## 4. Faz 3 — Bootstrap Loader (Projenin Kalbi)
**Dosya:** `loader/loader.s` — 82 komut, 328 bayt, RV32I, **kendi assembler'ımızla derlenir**

### 4.1 Ana döngü (paket alma + RAM'e yazma)
```asm
_start:
    LUI   s0, 0x20000          # s0 = UART base 0x2000_0000
main_loop:
find_aa:
    CALL  getc                 # SYNC ara: 0xAA bekle
    LI    t0, 0xAA
    BNE   a0, t0, find_aa
    CALL  getc                 # sonra 0x55
    LI    t0, 0x55
    BNE   a0, t0, find_aa

    LUI   s1, 0x10
    ADDI  s1, s1, -1           # crc = 0xFFFF (başlangıç)

    CALL  getc \  MV s2, a0 \  CALL crc16_byte   # CMD oku + CRC'ye kat
    CALL  getc \  MV s3, a0 \  CALL crc16_byte   # LEN oku + CRC'ye kat
    # ... ADDR'nin 4 baytı okunup s4'te birleştirilir, her biri CRC'ye katılır
```

### 4.2 DATA'yı RAM'e yazma (en kritik kısım)
```asm
    LI    s6, 0                # i = 0
    MV    s7, s4               # wptr = hedef adres (ADDR)
data_loop:
    BEQ   s6, s3, data_done    # i == LEN ise bitti
    CALL  getc                 # bir bayt al
    SB    a0, 0(s7)            # >>> UYGULAMAYI RAM'E YAZ <<<
    CALL  crc16_byte           # CRC'ye kat
    ADDI  s7, s7, 1            # işaretçi ilerle
    ADDI  s6, s6, 1            # sayaç
    J     data_loop
```
`SB a0, 0(s7)` satırı, host'tan gelen her baytı **doğrudan RAM'e** (0x3000+) yazar. Hocanın
"makine kodlarını RAM'in doğru adreslerine yaz" dediği iş tam bu satırda.

### 4.3 CRC kontrolü + ACK/NAK + JUMP
```asm
    # gelen CRC16 (2 bayt LE) -> s5
    BNE   s1, s5, send_nak     # hesaplanan != gelen -> NAK
    LI    t0, 0x02
    BEQ   s2, t0, do_jump      # CMD==START -> atla
    LI    a0, 0x06 \  CALL putc \  J main_loop   # değilse ACK
send_nak:
    LI    a0, 0x15 \  CALL putc \  J main_loop   # NAK
do_jump:
    JALR  x0, s4, 0            # >>> UYGULAMAYA ATLA (entry adresine) <<<
```
`JALR x0, s4, 0` = "uygulamanın giriş adresine atla" → işlemci artık uygulamayı koşar. Bu,
"reset hattını serbest bırakma"nın yazılımsal karşılığı.

### 4.4 Leaf altprogramlar (stack kullanmadan)
```asm
getc:                          # UART'tan bir bayt oku -> a0
    LW    t1, 4(s0)            # STATUS
    ANDI  t1, t1, 1            # rx_valid?
    BEQ   t1, x0, getc         # gelmediyse bekle (poll)
    LW    a0, 0(s0)            # DATA oku (rx_valid temizlenir)
    ANDI  a0, a0, 0xFF
    RET

crc16_byte:                    # s1 = CRC_update(s1, a0) — host/crc.py ile BİREBİR
    SLLI  t0, a0, 8 \  XOR s1, s1, t0      # crc ^= byte<<8   (XOR komutu burada!)
    ... 8 kez: bit15 test -> koşullu XOR 0x1021 ...
    RET
```
`crc16_byte`, `host/crc.py`'deki algoritmanın **birebir RV32I karşılığı**. ACK alınması =
iki tarafın CRC'sinin aynı olması (yoksa her paket NAK olurdu).

**`loader/build_loader.py`:** loader'ı derleyip `loader_init.vh` üretir ve SoC'a `mem_init.vh`
olarak kurar (`--install`). `loader/loader.ld`: `TEXT_ORIGIN=0x0000`.

---

## 5. Faz 3/4 — ISS ile Sentez-Öncesi Doğrulama
**Dosyalar:** `tools/iss.py`, `loader/test_loader.py`

### 5.1 `tools/iss.py` — RV32I Komut-Set Simülatörü
Linker'ın ürettiği **gerçek makine kodunu** Python'da çalıştırır; UART ve GPIO'yu modeller.
Komut çözme örneği (JALR, loader'ın atlama komutu):
```python
elif op == 0x67:              # JALR
    imm = _sext((inst >> 20) & 0xFFF, 12)
    t = next_pc
    next_pc = (R[rs1] + imm) & 0xFFFFFFFE
    R[rd] = t
```
UART modeli (loader'a paket akışını besler):
```python
class UartModel:
    def read(self, off):
        if off == 0x00: return self.rx.pop(0) if self.rx else 0   # DATA
        if off == 0x04: return (0 << 1) | (1 if self.rx else 0)   # STATUS.rx_valid
```

### 5.2 `loader/test_loader.py` — Gerçek loader'ı koştur
```python
ld = _build("loader/loader.s", ...)          # gerçek loader.bin
app = _build("apps/t1_arith_led.s", ...)     # gerçek uygulama
stream = host_paketleri(app, 0x3000)         # WRITE blokları + START
iss = ISS(uart=UartModel(rx_bytes=stream))
iss.load_image(ld, base=0); iss.run(entry=0, stop_on_pc=0x3000)
assert iss.mem[0x3000:...] == app            # RAM birebir mi?
assert uart.tx == bytes([ACK]*nblocks)       # her blok ACK'lendi mi?
```
**Üç test geçti:** (1) load+jump (RAM bayt-bayt doğru, pc→0x3000), (2) jump sonrası app koştu
(LED=42), (3) bozuk CRC → NAK → retransmit. **Sentez olmadan** loader'ın doğruluğu kanıtlandı.

---

## 6. Faz 1 (devamı) — `mem_init.vh` Köprüsü (En Kritik Debug Hikâyesi)
**Dosya:** `hex_emitter.py` (`write_verilog_init`) → `mem_init.vh` → `bram.v`

**Sorun:** Standart `$readmemh("blink.hex")` Gowin sentez aracında **sessizce yok sayılıyordu**
→ BRAM sıfır kalıyor → CPU `0x00000000 = NOP` çalıştırıyor → LED hiç yanmıyor.

**Çözüm:** Toolchain'e, belleği dolduran **açık Verilog deyimleri** üreten bir çıktı ekledik:
```python
# hex_emitter.py -> mem_init.vh içeriği:
    mem[0] = 32'h100002b7;
    mem[1] = 32'h00000313;
    ...
```
`bram.v` bunu `\`include "mem_init.vh"` ile alır. Header-guard (`\`ifdef BRAM_INIT_LOAD`)
sayesinde dosya yanlışlıkla standalone derlenirse hata vermez. Böylece init verisi
preprocessor seviyesinde **kesin** gömülür.

---

## 7. Faz 5 — Test Uygulamaları
**Klasör:** `apps/` — hepsi `app.ld` (TEXT_ORIGIN=0x3000) ile derlenir, UART'tan yüklenir.

**T1 — Aritmetik + LED (`t1_arith_led.s`):**
```asm
_start:
    LUI   t0, 0x10000        # GPIO/LED base 0x1000_0000
    LI    t1, 40
    LI    t2, 2
    ADD   t3, t1, t2         # 40 + 2 = 42
    SW    t3, 0(t0)          # LED = 42 = 0b101010
spin: J spin
```

**T2 — Döngü + sayaç (`t2_loop_blink.s`):** `ANDI`+`SW` ile 6-bit sayacı LED'e basar,
`LUI t3, 0x8` + `ADDI/BNE` gecikme döngüsüyle yavaşlatır → döngü ve dallanma testi.

**T3 — Fonksiyon + buton (`t3_func_button.s`):**
```asm
main:
    CALL  get_button         # alt program çağrısı (JAL/RET)
    BEQ   a0, x0, released
    LI    t1, 0x3F           # basılı -> 6 LED
    J     show
released:
    LI    t1, 0x09           # bırakıldı -> 0b001001
get_button:                  # leaf: GPIO+4'ten buton oku
    LW    a0, 4(s0) \  ANDI a0, a0, 1 \  RET
```
`apps/test_apps.py` üçünü de ISS'te doğrular (T1 LED=42, T2 sayaç monoton, T3 buton 0/1).

---

## 8. Proje 3 Dosya Envanteri (git'ten)

**YENİ dosyalar:**
```
host/crc.py, host/packet.py, host/host_loader.py, host/requirements.txt
loader/loader.s, loader/loader.ld, loader/build_loader.py, loader/test_loader.py
tools/iss.py
apps/t1_arith_led.s, apps/t2_loop_blink.s, apps/t3_func_button.s, apps/app.ld, apps/test_apps.py
fpga/tangnano9k_soc/uart.v
fpga/tangnano9k_soc/uart_echo_test/  (echo.s, uart_model_test.py, README)
fpga/tangnano9k_soc/mem_init.vh, loader_init.vh  (toolchain ürünleri)
```
**GÜNCELLENEN dosyalar:**
```
opcode_table.py        (XOR/XORI/LBU)
fpga/tangnano9k_soc/soc_top.v    (UART instance + 0x2 decode + buton)
fpga/tangnano9k_soc/bram.v       (8KB->16KB + mem_init.vh include)
fpga/tangnano9k_soc/gpio.v       (buton giriş register'ı)
fpga/tangnano9k_soc/tangnano9k.cst  (uart_tx=17, uart_rx=18, btn=3)
```

---

## 9. Sonuç — Proje 3'te Ne Başardık?

`kaynak → assembler (+XOR/XORI/LBU) → linker → .bin → host_loader (CRC paket) → UART →
loader (RV32I, RAM'e yaz + JUMP) → uygulama` zincirini **tamamen kendi kodumuzla** kurduk,
sentezden önce **ISS'te gerçek makine kodu çalıştırarak doğruladık** ve **Tang Nano 9K'da
fiziksel olarak çalıştırdık**. Loader, işlemcinin kendi komut setiyle yazılmış bir sistem
yazılımı olarak hocanın isteğini birebir karşılıyor.
