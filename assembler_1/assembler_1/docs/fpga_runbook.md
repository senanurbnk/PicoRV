# FPGA Runbook — Board Elime Geçince Yapılacaklar

> Tüm yazılım (toolchain, host, loader, 3 uygulama) FPGA'siz doğrulandı (ISS +
> self-test). Geriye yalnızca Gowin sentezi + Tang Nano 9K üzerinde fiziksel
> doğrulama kaldı. Bu doküman o adımları sırayla verir.
>
> Çalışma dizini: `assembler_1/assembler_1/`. Board: USB-C ile bağlı.

---

## 0) Ön koşullar (bir kez)
- Gowin EDA (Education, lisanslı) kurulu. ✓ (sende var)
- `pip install -r host/requirements.txt` (pyserial). ✓
- Aygıt Yöneticisi → Ports (COM & LPT) → Tang Nano 9K'nın **COM numarasını** not et
  (ör. COM5). BL702 köprüsü hem JTAG (programlama) hem UART sağlar.

---

## ⚠️ Önemli tuzak: iki kopya `src/`
Gowin projesi `fpga/tangnano9k_soc/fpga_project/` altında ve **kendi `src/` kopyasını**
kullanıyor. Güncel kaynaklar `fpga/tangnano9k_soc/` kökünde. Sentezden önce **güncel
dosyaları proje `src/`'ine kopyala** (veya projeye yeniden ekle):

```bash
cd fpga/tangnano9k_soc
cp uart.v soc_top.v bram.v gpio.v   fpga_project/src/
cp tangnano9k.cst                    fpga_project/src/
cp mem_init.vh mem.hex               fpga_project/src/    # BRAM init
```
> `uart.v` Gowin projesine **yeni dosya** olarak da eklenmeli (Design Sources → Add File),
> ilk seferde `src/` listesinde yoksa.

---

## 1) Faz 1 — UART echo bring-up (UART donanımını kanıtla)
BRAM init şu an **echo firmware** (`mem_init.vh` = echo.s). Direkt sentezle:

1. Gowin → **Run All** (Synthesize → P&R → bitstream).
   - Beklenen: LUT ~1300, BSRAM birkaç blok, timing 27 MHz'de rahat.
   - Hata çıkarsa: §Troubleshooting.
2. **Tools → Programmer** → Scan → **SRAM Program** (geçici, hızlı test).
3. Host'tan echo testi:
   ```bash
   cd ../../host
   python host_loader.py --port COM5 --baud 9600 --echo-test
   ```
   **Beklenen:** `ECHO TEST OK: 256 bayt (0x00..0xFF) birebir geri geldi`
   - Yanıt yok → COM doğru mu? tx/rx ters mi? baud 9600 mi?
   - Bozuk bayt → baud/clock; önce 9600'de kal.

✅ Bu geçince UART RX+TX + MMIO + CPU'nun BRAM'den koşması fiziksel kanıtlanmış olur.

---

## 2) Faz 3/4 — Loader'ı board'a al ve uygulama yükle
Echo geçtiyse BRAM'i **loader**'a çevir:

```bash
cd ..                      # assembler_1/assembler_1
python loader/build_loader.py --install
#   mem_init.vh/mem.hex -> loader  (boot firmware artik loader)
cp fpga/tangnano9k_soc/mem_init.vh fpga/tangnano9k_soc/mem.hex fpga/tangnano9k_soc/fpga_project/src/
```
Gowin → **Run All** → **SRAM Program** (loader artık BRAM'de, reset'te koşar).

Uygulamayı UART'tan yükle (T1):
```bash
cd host
python host_loader.py --port COM5 --baud 9600 \
    --bin ../apps/t1_arith_led.bin --addr 0x3000 --entry 0x3000 -v
#   Her blok -> ACK ; sonra START -> loader 0x3000'e atlar
```
**Beklenen:** LED'ler **42 = 0b101010** gösterir. (ISS'te de bu çıktı.)

> `.bin` dosyaları repoda hazır (`apps/*.bin`). Yeniden üretmek için:
> `python run_link.py apps/t1_arith_led.s -T apps/app.ld -o apps/t1_arith_led`

---

## 3) Faz 5 — Üç testi sırayla göster
```bash
cd host
# T1: aritmetik -> LED 42
python host_loader.py --port COM5 --baud 9600 --bin ../apps/t1_arith_led.bin
# T2: LED sayaç/blink (döngü, dallanma)
python host_loader.py --port COM5 --baud 9600 --bin ../apps/t2_loop_blink.bin
# T3: fonksiyon + buton (S1, pin 3) — basılıyken 6 LED, bırakınca 0b001001
python host_loader.py --port COM5 --baud 9600 --bin ../apps/t3_func_button.bin
```
Her yüklemeden sonra **board'u reset'leyip** (S2, pin 4) yeni uygulamayı yükle —
loader tekrar paket beklemeye başlar. (Reset → loader yeniden çalışır.)

**Sağlamlık testi (Faz 5):** Aynı uygulamayı 10 kez ardışık yükle, hepsi ACK'lensin.
Kasıtlı hata: host bir bloğu bozsa loader NAK verir, host retransmit eder (ISS'te
kanıtlandı; board'da da gözlemle).

---

## 4) 115200 baud'a çıkış (opsiyonel, hız metriği için)
`fpga/tangnano9k_soc/soc_top.v` içinde:
```verilog
localparam integer UART_BAUD = 9600;   // -> 115200 yap
```
`src/`'e kopyala → Run All → SRAM Program. Host'ta `--baud 115200`. Yükleme süresi
~12× kısalır (rapor §3.2 metriği).

---

## 5) Kalıcı yapmak (sunum/demo için)
Programmer'da **Embedded Flash Program** seç (SRAM yerine). Board her açıldığında
loader otomatik koşar; sadece host'tan uygulama yüklemen yeterli.

---

## Troubleshooting
| Belirti | Olası neden / çözüm |
|---------|---------------------|
| Sentez `CT1136 bank vccio` | LED/buton pinleri LVCMOS18 olmalı (Bank3/1.8V). `.cst` zaten öyle. |
| `uart.v` bulunamadı | Gowin projesine Add File ile ekle; `src/`'e kopyalandı mı? |
| Echo yanıt yok | COM no? tx(17)/rx(18) ters mi? Programmer SRAM yaptı mı? baud 9600? |
| LED hep kapalı | BRAM init yüklendi mi? `mem_init.vh` `src/`'de güncel mi? reset (S2) basılı kalmıyor mu? |
| Uygulama yüklenmiyor (NAK döngüsü) | baud uyumsuz; CRC kapsamı (host=loader) — ikisi de CRC-16/CCITT-FALSE; `--baud` eşle. |
| T3 buton tepki vermiyor | S1 (pin 3) doğru mu? active-low + pull-up; soc_top 2-FF sync + invert yapıyor. |
| Sayım çok hızlı (T2) | `t2_loop_blink.s` içinde `LUI t3, 0x8` → `0x400` yap, yeniden assemble+yükle. |

## Doğrulama izleri (rapor için topla)
- `host_loader.py -v` çıktısı (blok ACK'leri, yükleme süresi).
- LED fotoğrafı/videosu (T1=42, T2 sayaç, T3 buton).
- UART terminal ekran görüntüsü.
- Gowin kaynak raporu (LUT/FF/BSRAM) — rapor §3.2.
