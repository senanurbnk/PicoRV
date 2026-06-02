# loader/ — RV32I Yazılımsal Bootstrap Loader

Proje 3'ün kalbi: PicoRV32 üzerinde koşan, **kendi assembler+linker'ımızla** derlenen
bootstrap loader (hocanın isteği: PicoRV'nin kendi komut setiyle). Reset sonrası
`0x0000`'dan başlar, UART'tan paket alır, CRC-16/CCITT-FALSE ile doğrular, uygulamayı
`0x3000`'e yazar, START komutunda uygulamaya `JALR` ile atlar.

## İçerik
| Dosya | Ne |
|-------|----|
| `loader.s` | RV32I loader (FSM: SYNC→HEADER→ADDR→DATA→CRC→ACK/NAK→JUMP). 82 komut, 328B. Yalnız desteklenen 23-komut alt kümesi. |
| `loader.ld` | Linker script, `TEXT_ORIGIN=0x0000`. |
| `build_loader.py` | `loader.s`→`loader_init.vh`+`loader.hex` üretip SoC klasörüne kopyalar. |
| `test_loader.py` | **ISS doğrulaması** (FPGA'siz): gerçek loader makine kodunu host paketleriyle koşturur. |

## FPGA'siz doğrulama (yapıldı ✓)
`tools/iss.py` (RV32I komut-set simülatörü) loader'ın GERÇEK makine kodunu çalıştırır;
`host/packet.py` paket üretir. Üç test:
```bash
python loader/test_loader.py
#  [OK] load+jump: 2 blok ACK'lendi, RAM birebir, pc->0x3000
#  [OK] jump sonrasi uygulama kostu: GPIO/LED = 42 (0b101010)
#  [OK] bozuk CRC -> NAK, retransmit -> 2x ACK, RAM birebir
```
Bu, sentez OLMADAN şunları kanıtlar:
- Loader komut akışı (SYNC/HEADER/DATA/CRC/JUMP) doğru.
- Loader CRC'si `host/crc.py` ile **birebir** (yoksa her blok NAK olurdu).
- Bellek yazımı + endianness doğru (RAM == gönderilen app).
- ACK/NAK + START/JUMP doğru.

> Bu donanım testinin yerine geçmez; UART/timing ayrıca Gowin sentezi + board ile
> doğrulanacak (echo bring-up: `fpga/tangnano9k_soc/uart_echo_test/`).

## Loader'ı board'a almak (echo bring-up geçtikten sonra)
```bash
python loader/build_loader.py --install     # mem_init.vh/mem.hex -> loader
# Gowin: src/ senkronla -> Run All -> Programmer
cd host
python host_loader.py --port COMx --baud 9600 --bin ../apps/t1_arith_led.bin \
                      --addr 0x3000 --entry 0x3000
# LED'ler 42 = 0b101010 gösterir
```

## Register kullanımı (loader.s)
`s0`=UART base, `s1`=crc, `s2`=cmd, `s3`=len, `s4`=addr, `s5`=rx_crc, `s6`=i, `s7`=wptr.
Leaf altprogramlar (`getc`/`putc`/`crc16_byte`) yalnız `t*`/`a0`/`ra` kullanır, başka
altprogram çağırmaz → tek seviye `ra`, **stack gerekmez**.

Detay: `../docs/proje3_plan.md` §4.4, `../docs/memory_map.md`.
