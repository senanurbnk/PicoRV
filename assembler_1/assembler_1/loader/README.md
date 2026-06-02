# loader/ — RV32I Yazılımsal Bootstrap Loader

Proje 3'ün kalbi: PicoRV32 üzerinde koşan, **kendi assembler+linker'ımızla** derlenen
bootstrap loader. Reset sonrası `0x0000`'dan başlar, UART'tan paket alır, CRC doğrular,
uygulamayı `0x3000`'e yazar, START komutunda uygulamaya `jalr` ile atlar.

## İçerik (fazlarla gelecek)
| Dosya | Ne | Faz |
|-------|----|-----|
| `loader.s` | RV32I loader (FSM: IDLE→SYNC→HEADER→DATA→CRC→ACK/NAK→DONE→JUMP) | 3–4 |
| `loader.ld` | Linker script, `TEXT_ORIGIN=0x0000` (boot bölgesi) | 3 |
| `build_loader.py` | `run_link.py`'ı çağırıp `loader_init.vh` üretir → SoC'a kopyalar | 3 |

## Kısıtlar
- **Yalnızca desteklenen komut alt kümesi** kullanılır (23 komut; XOR/XORI/LBU Faz 0'da eklendi).
- Tek dosya → cross-file relocation yok.
- MMIO erişimi: `LW`/`SW` ile UART_DATA(0x20000000)/UART_STATUS(0x20000004).
- CRC-16/CCITT: XOR/XORI/SLLI/SRLI/ANDI ile bit-bit veya tablo.
- JUMP: entry (0x3000) `LUI`+`ADDI` ile register'a, `JALR x0, 0(reg)`.

Detaylı tasarım: `../docs/proje3_plan.md` §4.4, `../docs/memory_map.md`.
