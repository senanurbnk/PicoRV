# Tang Nano 9K + PicoRV32 LED Counter — Build Rehberi

Bu klasör, projenin **donanım** (SoC) tarafıdır. Yazılım tarafı
(`firmware/blink/`) önce derlenmeli; üretilen `blink.hex` BRAM
init dosyası olarak buraya kopyalanır.

## Mimari özet

```
   firmware/blink/main.s          fpga/tangnano9k_soc/soc_top.v
                +                              +
   firmware/blink/delay.s         fpga/tangnano9k_soc/bram.v
                |                  fpga/tangnano9k_soc/gpio.v
                v                  vendor/picorv32/picorv32.v
   [run_link.py]                                |
                |                               v
                v                  [Gowin EDA: synth + P&R]
        blink.hex (Verilog $readmemh)           |
                |                               v
                +----------------------> blink_soc.fs (bitstream)
                                                |
                                                v
                                         Tang Nano 9K
```

## Bellek haritası

| Adres aralığı            | Aygıt   | Açıklama                          |
|--------------------------|---------|-----------------------------------|
| `0x00000000-0x00001FFF`  | BRAM    | 8 KB, picorv32 reset PC = 0       |
| `0x10000000-0x100000FF`  | GPIO    | Alt 6 bit → LED'ler (1 = ON)      |
| diğer                    | yok     | rdata=0 dönülür (hata yok)        |

## Build adımları

### 1) Yazılımı derle

```bash
cd assembler_1/assembler_1
python run_link.py firmware/blink/main.s firmware/blink/delay.s \
                   -T firmware/blink/tangnano9k.ld \
                   -o firmware/blink/build/blink -v
```

`firmware/blink/build/blink.hex` üretilir. Bu dosyayı SoC klasörüne
kopyala (Gowin proje kökünde olmalı):

```bash
cp firmware/blink/build/blink.hex fpga/tangnano9k_soc/blink.hex
```

### 2) Gowin EDA projesini kur

1. **Gowin EDA** (Education edition, lisanslı) aç.
2. `File → New → FPGA Design Project`. Proje yolu: `fpga/tangnano9k_soc/`.
3. **Device seçimi:**
   - Series: **GW1NR**
   - Device: **GW1NR-LV9QN88PC6/I5**
   - Package: **QFN88**
   - Speed: **C6/I5**
4. **Design Sources** sekmesinden ekle (sağ tık → Add Files):
   - `vendor/picorv32/picorv32.v`
   - `fpga/tangnano9k_soc/bram.v`
   - `fpga/tangnano9k_soc/gpio.v`
   - `fpga/tangnano9k_soc/soc_top.v` (Top-level olarak işaretle)
5. **Constraints** sekmesinden:
   - `tangnano9k.cst` (Physical) ekle
   - `tangnano9k.sdc` (Timing) ekle
6. **Project → Configuration → Place & Route → Generate Bitstream File**
   seçeneğini işaretle. (Default'ta zaten açık.)

> **Önemli:** `blink.hex` Gowin proje kökünde (yani `.gprj` dosyasının
> yanında) olmalı, çünkü `bram.v` içindeki `$readmemh("blink.hex")`
> göreceli yol kullanır. Aksi takdirde sentezleme aşamasında "init data
> empty" uyarısı alır ve BRAM tüm sıfırla başlar.

### 3) Sentez + Place & Route

`Process` panelinden sırayla:
1. **Synthesize** (GowinSynthesis)
2. **Place & Route**
3. Bitstream `impl/pnr/<proje>.fs` altına çıkar.

Beklenen kaynak kullanımı:
- LUT: ~1100 / 8640 (~13%)
- FF: ~600 / 6480 (~9%)
- BSRAM: 4 / 26 (8 KB için)
- Timing: 27 MHz için yeterli marj (Fmax > 80 MHz tipik)

### 4) Bitstream'i Tang Nano 9K'ya yükle

İki yol var:

**Yol A — Gowin Programmer (GUI):**
1. Tang Nano 9K'yı USB-C ile bağla.
2. `Tools → Gowin Programmer` aç.
3. **Scan** → cihaz görünmeli (`GW1NR-9` rev x.x).
4. **File:** `<proje>/impl/pnr/<proje>.fs`
5. **Operation:**
   - **SRAM Program** (geçici, güç kesilince silinir — test için)
   - **Embedded Flash Program** (kalıcı — bitince LED hemen sayar)
6. **Program/Configure** bas.

**Yol B — openFPGALoader (komut satırı, daha hızlı):**
```bash
# SRAM (geçici)
openFPGALoader -b tangnano9k impl/pnr/blink_soc.fs

# Flash (kalıcı)
openFPGALoader -b tangnano9k -f impl/pnr/blink_soc.fs
```

### 5) Beklenen davranış

- LED'ler 6-bit binary sayar.
- Her artış arası ~150-400 ms (delay.s'deki `LUI t2, 0x100` ile ayar).
- BTN1'e (S1) basıldığında reset → sayım sıfırdan başlar.

## Hata ayıklama ipuçları

**LED hiç yanmıyor:**
- `blink.hex` proje kökünde mi? (Sentez log'unda `$readmemh: open file`
  uyarısı varsa yok demektir.)
- Reset (BTN1) sürekli basılı kalmıyor mu? (cst'de `PULL_MODE=UP` ile
  zaten yukarı çekildi.)
- LED pinleri board revizyonuna göre farklı olabilir — board üstündeki
  silkscreen ile cst'deki pin numaralarını karşılaştır.

**LED'ler tüm yanıyor sürekli:**
- CPU illegal instruction'da takılmış olabilir. `CATCH_ILLINSN(0)` ile
  trap kapalı; takılırsa BRAM'daki kod doğru mu kontrol et.
- `blink.hex` formatı: her satır tek 32-bit hex word olmalı, başında
  `@addr` olmamalı. (run_link.py default çıktısı zaten doğru.)

**Saymıyor, sabit tek değer:**
- Delay sayım değeri çok büyük olabilir; `delay.s` içinde `LUI t2, 0x100`
  yerine `LUI t2, 0x010` deneyebilirsin.

## Yazılım değişikliği yaparsan

`firmware/blink/*.s` dosyalarını değiştirdikten sonra:
1. `python run_link.py ...` ile yeniden üret.
2. Yeni `blink.hex`'i proje köküne kopyala.
3. **Gowin: Synthesize** + **Place & Route** baştan.
4. Yeniden program.

(Tek başına bitstream'i güncelle yok — BRAM init Verilog'a gömülüdür.)
