# Bellek Haritası — Proje 3 (Loader + Uygulama)

> Bu harita `soc_top.v` adres çözücüsü ve loader/app linker script'leriyle
> **birebir** tutulmalıdır. Decode: `mem_addr[31:28]` (üst nibble).

## Genel Harita

```
0x0000_0000 ┌─────────────────────────────┐  [31:28]=0x0 → BRAM (16 KB)
            │ LOADER .text  (4 KB)         │  PROGADDR_RESET = 0x0000_0000
0x0000_0FFF │                             │  loader_init.vh ile gömülü
0x0000_1000 ├─────────────────────────────┤
            │ (boş / loader heap-stack)   │
0x0000_2000 │  ← STACKADDR (aşağı büyür)  │
0x0000_2FFF ├─────────────────────────────┤
0x0000_3000 │ UYGULAMA .text + .data (4KB)│  Entry = 0x0000_3000
0x0000_3FFF │  UART'tan runtime yüklenir  │  (sentezde BOŞ; sıfır init)
            └─────────────────────────────┘
0x1000_0000   GPIO   [31:28]=0x1   alt 6 bit → LED (active-low, mevcut)
0x2000_0000   UART   [31:28]=0x2   RX/TX/STATUS (YENİ)
diğer         rdata = 0 (no-op, CPU takılmaz)
```

## Adres Decode (soc_top.v)
| `mem_addr[31:28]` | Aygıt | Word adresi |
|-------------------|-------|-------------|
| `4'h0` | BRAM (16 KB) | `mem_addr[13:2]` (4096 word) |
| `4'h1` | GPIO | — (tek register) |
| `4'h2` | UART | `mem_addr[3:2]` (DATA/STATUS/DIV) |
| diğer | yok | rdata=0 |

## BRAM değişikliği
- `bram.v`: `ADDR_BITS 11 → 12` (8 KB → 16 KB). `waddr/raddr` = `mem_addr[13:2]`.
- Init: yalnız **loader** gömülür (`loader_init.vh`). Uygulama bölgesi (0x3000+) sıfır
  başlar, runtime'da UART üzerinden dolar.

## UART MMIO (0x2000_0000)
| Offset | Adres | İsim | Erişim | Açıklama |
|--------|-------|------|--------|----------|
| +0x00 | 0x2000_0000 | UART_DATA | R/W | Oku: rx byte [7:0]; Yaz: tx byte |
| +0x04 | 0x2000_0004 | UART_STATUS | R | bit0=rx_valid, bit1=tx_busy |
| +0x08 | 0x2000_0008 | UART_DIV | R/W | (ops.) baud bölücü |

## Linker script profilleri
```
# loader/loader.ld
TEXT_ORIGIN = 0x00000000
TEXT_LENGTH = 0x00001000
DATA_ORIGIN = 0x00001000
DATA_LENGTH = 0x00001000
ENTRY       = _start

# apps/app.ld
TEXT_ORIGIN = 0x00003000
TEXT_LENGTH = 0x00001000
DATA_ORIGIN = 0x00003800
DATA_LENGTH = 0x00000800
ENTRY       = _start
```

## Saat / Baud
- clk = 27 MHz (Tang Nano 9K kristal, pin 52).
- Baud bölücü ≈ clk/baud. 9600 → ~2812 ; 115200 → ~234. (bring-up: 9600.)

## Doğrulama notları
- 0x3000 = 12288 < 16384 (16 KB) → app bölgesi BRAM içinde. ✓
- loader (0x0000-0x0FFF) ↔ app (0x3000-0x3FFF) ayrık → loader app'i yazarken kendini ezmez. ✓
- STACKADDR=0x2000 loader bölgesinin üstünde, app bölgesinin altında. Derin recursion yoksa güvenli.
- UART pinleri: **Sipeed Tang Nano 9K şemasından doğrulanacak** (BL702 USB-UART köprüsü;
  MSPI ikili-amaçlı pinlerle çakışmamalı).
