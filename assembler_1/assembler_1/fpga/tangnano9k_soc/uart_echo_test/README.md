# Faz 1 — UART Bring-up (Echo Testi)

Amaç: SoC'a eklenen `uart.v`'yi gerçek donanımda doğrulamak. Echo firmware'i
(kendi toolchain'imizle derlenmiş) BRAM'e gömülür; PC'den gönderilen her bayt
geri yansır. Bu geçerse UART RX+TX, MMIO decode (0x2000_0000) ve CPU'nun
BRAM'den koşması kanıtlanmış olur.

## Sentez öncesi yazılım doğrulaması (FPGA'siz, burada yapıldı)
```bash
# 1) Echo firmware kendi toolchain'imizle derlenir
python ../../../run_link.py echo.s -T echo.ld -o echo
#   -> echo.bin / echo.hex / echo_init.vh (11 komut, 44B); encode birebir doğrulandı

# 2) UART FSM bit-zamanlaması (shift yönü, 8N1, orta-bit örnekleme)
python uart_model_test.py
#   -> 0x00/0xFF/0xAA/0x55 dahil tüm baytlar loopback'te birebir
```

## Gowin tarafı (kullanıcı, board ile)
1. **mem_init.vh hazır:** `echo_init.vh` zaten `../mem_init.vh`'ye kopyalandı
   (bram.v bunu `\`include` eder). Echo firmware'i değişirse:
   ```bash
   python ../../../run_link.py echo.s -T echo.ld -o echo
   cp echo_init.vh ../mem_init.vh   ;  cp echo.hex ../mem.hex
   ```
2. **Gowin projesine yeni dosya ekle:** `uart.v` (Design Sources). `soc_top.v`,
   `bram.v`, `tangnano9k.cst` güncellendi — Gowin proje `src/` kopyalarını da
   senkronla (veya dosyaları yeniden ekle).
   > Not: `fpga_project/src/` altında ayrı kopyalar var; Gowin onları kullanır.
   > Bu klasördeki güncel `.v`/`.cst`'leri oraya kopyala.
3. **Pinler:** `tangnano9k.cst` → `uart_tx`=17, `uart_rx`=18 (LVCMOS33, Bank2).
4. **Run All** → bitstream → Programmer (SRAM Program yeterli).

## Host tarafı testi (board programlandıktan sonra)
```bash
cd ../../../host
python host_loader.py --port COM5 --baud 9600 --echo-test
#   -> "ECHO TEST OK: 256 bayt (0x00..0xFF) birebir geri geldi"
```
`--port`'u kendi COM numaranla değiştir (Aygıt Yöneticisi → Ports).
Bring-up'ta **9600** baud; çalışınca soc_top.v'deki `UART_BAUD`'u 115200 yapıp
yeniden sentezle.

## Sorun giderme
- **Hiç yanıt yok:** COM portu doğru mu? `uart_tx`/`uart_rx` ters bağlanmış olabilir
  (FPGA tx=17 → PC rx). Baud uyumsuzsa bozuk bayt gelir → önce 9600.
- **Bozuk baytlar:** baud bölücü `UART_BAUD`/clk uyumsuz; 27 MHz doğru mu.
- **İlk bayt kayıp:** reset sonrası ilk transaction; `--echo-test` 256 bayt yollar,
  ilk farkı raporlar.
