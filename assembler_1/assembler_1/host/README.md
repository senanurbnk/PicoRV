# host/ — PC Tarafı Yükleyici (UART)

`run_link.py`'ın ürettiği `app.bin`'i okur, paketlere böler, CRC ekler, seri porttan
FPGA'deki loader'a gönderir, ACK/NAK yönetir, sonunda START (jump) paketi yollar.

## İçerik (fazlarla gelecek)
| Dosya | Ne | Faz |
|-------|----|-----|
| `crc.py` | CRC-16/CCITT (poly 0x1021). Loader ile **birebir** aynı algoritma. Birim testli. | 2 |
| `packet.py` | Paket çerçeveleme: `SYNC(AA55)|CMD|LEN|ADDR(4LE)|DATA|CRC16`. encode/decode. | 2 |
| `host_loader.py` | pyserial; blok blok gönder, ACK(0x06)/NAK(0x15)+retry+timeout, START. | 2,4 |
| `requirements.txt` | `pyserial` | 0 |

## CLI (hedef)
```
python host_loader.py --port COM5 --baud 115200 --bin app.bin --addr 0x3000 --entry 0x3000
python host_loader.py --port COM5 --ping        # Faz 1 echo/ping testi
```

## Protokol (loader ile birebir — docs/proje3_plan.md §4)
- CMD: 0x01=WRITE_BLOCK, 0x02=START(jump), 0x03=PING
- CRC16: SYNC hariç CMD..DATA üzerinden
- Blok boyu 4'ün katı (word hizalı) → loader SW ile yazar
- Endianness: PicoRV32 little-endian; host bayt sırası = loader SW word sırası (Faz 3'te geri-okuma ile doğrulanır)
