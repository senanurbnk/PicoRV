# apps/ — Yüklenecek Test Uygulamaları

Loader'ın UART'tan yükleyip çalıştıracağı uygulamalar. **Yalnızca desteklenen 23 komutluk
alt küme.** Hepsi `app.ld` (TEXT_ORIGIN=0x3000) ile linklenir, `run_link.py` ile `.bin` üretilir,
`host_loader.py` ile gönderilir.

## Testler (artan karmaşıklık — docs/proje3_plan.md §6)
| Test | Dosya | İçerik | Sınar |
|------|-------|--------|-------|
| T1 | `t1_arith_led.s` | aritmetik (ADD/SUB), sonucu GPIO'ya SW → LED | loader doğru yükledi mi (en basit kanıt) |
| T2 | `t2_loop_blink.s` | delay döngüsü + LED blink/sayaç (BEQ/BNE) | döngü, dallanma, zamanlama |
| T3 | `t3_func_button.s` | JAL/JALR alt program + butona göre dallanma (GPIO read) | fonksiyon çağrısı, PC-bağıl, GPIO girişi |

> T3 buton girişi için `gpio.v`'ye read-only buton register'ı gerekebilir (Faz 5).

## Bireysel sunum provası
Her üye en az bir testte canlı küçük değişiklik (blink hızı / LED deseni / dönüş değeri)
yapıp **assemble→link→host_loader→FPGA** zincirini akıcı koşturabilmeli.
