# Proje 3 — Tanıtım Videosu Senaryosu (≤ 5 dk, özgeçmiş kalitesinde)

> Hocanın notu: *"Video içeriği salt program çalışması olmamalı; özgeçmişinize
> ekleyebileceğiniz kalitede olmalı."* Bu senaryo bunu hedefler: sadece "LED yandı"
> değil — **özgünlük, mühendislik derinliği, doğrulama metodolojisi ve sürdürülebilir
> katkı** anlatan, akıcı ve görsel bir film.
>
> Toplam hedef süre: **4:30–4:55** (5 dk sınırının altında, tampon bırak).
> Anlatım dili Türkçe; özgeçmiş için **İngilizce altyazı** eklemen şiddetle önerilir.

---

## 0) Filmin tek cümlelik konumlandırması (akılda kalan mesaj)

> "Kaynak koddan fiziksel donanıma kadar **tamamen kendi yazdığımız araç zinciriyle** —
> assembler, linker ve PicoRV32'nin kendi komut setiyle yazılmış bir bootstrap loader ile —
> bir programı UART üzerinden FPGA'ya yükleyip çalıştırdık; ve bunu sentezden **önce**
> kendi yazdığımız bir komut-set simülatöründe doğruladık."

Bu cümle videonun açılışında ve kapanışında (farklı kelimelerle) geçmeli. İzleyici
videodan **tek bir şey** hatırlayacaksa bu olmalı.

### Bizi "normal akıştan" ayıran 4 özgünlük (videoda mutlaka vurgula)
1. **Loader, PicoRV32'nin kendi RV32I komut setiyle yazıldı** ve **kendi
   assembler+linker'ımızla** derlendi — hazır gcc/ld değil. (Hocanın isteği birebir.)
2. **Sentezden önce doğrulama:** Kendi yazdığımız RV32I komut-set simülatörü (ISS)
   gerçek makine kodunu çalıştırıp loader'ı, CRC'yi, bellek yazımını ve jump'ı kanıtladı.
3. **CRC-16, host (Python) ve loader (RV32I) tarafında birebir aynı** — ACK alınması
   bunun fiziksel kanıtı (uyuşmasa her paket NAK olurdu).
4. **Araç zinciri ↔ donanım köprüsü:** Gowin'in `$readmemh`'i sessizce yok sayması
   sorununu, toolchain'in ürettiği `mem_init.vh` include mekanizmasıyla çözdük.

---

## 1) Kayıt öncesi hazırlık (çekime başlamadan)

### Ekipman / yazılım
- **Ekran kaydı:** OBS Studio (ücretsiz) — 1920×1080, 30 fps, ayrı ses kanalı.
- **Mikrofon:** kulaklık mikrofonu bile olur; sessiz oda. Ses, görüntüden önemli.
- **Telefon/kamera:** FPGA kartının ve LED'lerin yakın çekimi için (tripod/sabit zemin).
- **Kurgu:** CapCut / DaVinci Resolve (ücretsiz) — kesme, başlık kartı, altyazı, B-roll.

### Çekime hazır bekletilecekler ("sahne dekoru")
- Terminal: `assembler_1/assembler_1/` dizininde açık, font büyük (en az 16–18 pt),
  koyu tema. Komut geçmişi temiz.
- Editör (VS Code): şu dosyalar sekmede açık ve hazır: `loader/loader.s`,
  `apps/t1_arith_led.s`, `host/crc.py`, `fpga/tangnano9k_soc/uart.v`.
- draw.io diyagramları: `docs/report/drawio/fig_arch.drawio` ve `fig_fsm.drawio`
  açık (veya PNG'leri tam ekran). Bunlar videonun "şema" anları.
- FPGA kartı bağlı, **9600 baud bitstream yüklü**, reset'e basınca loader bekliyor.
- Kamera açısı: LED'ler net görünecek şekilde, üstten/açılı yakın çekim.

> **Önemli:** 115200 baud çalışmıyor (FPGA baud'u sentez-zamanı sabit). Videoda
> **sadece 9600** göster; 115200'ü canlı denemeye kalkma.

### Önceden çekilecek B-roll (kurguda araya serpiştirilir)
- Kart yakın çekimi (LED'ler sönükken ve yanarken).
- Terminalde komutların akışı (hızlandırılmış kullanılabilir).
- Kod kaydırma (loader.s / crc.py) — kısa, estetik.

---

## 2) Sahne sahne senaryo

> Format: **[süre] SAHNE — Ekranda ne var | Ne söylüyorsun (anlatım).**
> Anlatım metinleri "okunabilir" yazıldı; kendi cümlelerinle doğallaştır.

### [0:00–0:20] SAHNE 1 — Açılış kartı (hook)
**Ekran:** Başlık kartı — proje adı, grup üyeleri, ders. Arka planda kısa bir LED
sayaç klibi (B-roll). Alt köşede repo adı.
**Anlatım:**
> "Merhaba. Bu videoda, RISC-V tabanlı PicoRV32 işlemcisi için **sıfırdan kendi
> yazdığımız** bir araç zincirini ve bu araç zinciriyle derlediğimiz bir bootstrap
> loader'ı, gerçek bir FPGA üzerinde çalışırken göstereceğiz. Sadece çalıştığını değil,
> **nasıl ve neden** bu şekilde tasarladığımızı da anlatacağız."

### [0:20–0:55] SAHNE 2 — Problem ve sistem mimarisi
**Ekran:** `fig_arch` diyagramı (tam ekran). Anlatırken ilgili bloğun üzerine fare/işaret.
**Anlatım:**
> "Problem şu: Bir programı kaynak kodundan alıp fiziksel bir işlemcide çalıştırmak.
> Bunun için üç parça yazdık. Solda **bilgisayar tarafı**: kendi assembler'ımız kaynağı
> nesne koduna, linker'ımız çalıştırılabilir bir bellek imajına çeviriyor; host
> uygulaması bunu CRC-16 ile korunan paketler hâlinde UART'tan gönderiyor. Sağda
> **FPGA tarafı**: PicoRV32 çekirdeği, 16 KB blok bellek, ve bizim eklediğimiz UART ile
> GPIO çevre birimleri. İkisini birbirine bağlayan da bu **loader**."

### [0:55–1:20] SAHNE 3 — Özgünlük #1: loader işlemcinin kendi dilinde
**Ekran:** `loader/loader.s` (kaydır), sonra `run_link.py` ile loader'ın derlendiği an
(`build_loader.py` çıktısı: "loader.bin 328B / 82 komut").
**Anlatım:**
> "Buradaki en kritik tasarım kararı: loader'ı hazır bir derleyiciyle değil,
> **PicoRV32'nin kendi RV32I komut setiyle** yazdık ve yine **bu projede yazdığımız
> assembler ve linker ile** derledik. Yani araç zincirimizi ikinci kez, sistem-yazılımı
> seviyesinde kanıtlamış olduk. Loader 328 bayt, 82 komut; reset sonrası bellekte hazır
> bekliyor."

### [1:20–2:35] SAHNE 4 — CANLI DEMO (videonun kalbi)
**Ekran:** Bölünmüş veya sırayla: (a) terminal, (b) FPGA kartı yakın çekim.
Aşağıdaki komutları **canlı** çalıştır; kamerayı LED'lere çevir.

**4a — Derle (terminal):**
```
python run_link.py apps/t1_arith_led.s -T apps/app.ld -o apps/t1_arith_led -v
```
> "Önce çalıştıracağımız uygulamayı kendi araç zincirimizle derliyoruz: assembler →
> linker → ikili dosya. Çıktı, 0x3000 adresine yerleşecek küçük bir programdır."

**4b — Yükle (terminal):**
```
cd host
python host_loader.py --port COM5 --baud 9600 --bin ../apps/t1_arith_led.bin --addr 0x3000 --entry 0x3000 -v
```
> "Şimdi host uygulamamız bu programı paketlere bölüp UART üzerinden FPGA'ya yolluyor.
> Her paketin sonunda CRC-16 var. Dikkat: FPGA'daki loader her paketi aldıkça **ACK,
> yani 0x06** dönüyor — ekranda görüyorsunuz. Tüm bloklar gidince loader programın
> başlangıç adresine atlıyor."

**4c — Sonuç (kamera → kart):**
> "Ve işte: linker'ımızın hesapladığı, host'umuzun yolladığı, loader'ımızın belleğe
> yazıp çalıştırdığı program fiziksel olarak çalışıyor — LED deseni **42**, yani ikili
> tabanda 101010. Bu, 40 artı 2'nin sonucu."

**4d — Diğer testler (hızlı):** T2 (sayaç) ve T3 (butona basınca desen değişiyor) yükle.
> "İkinci testte bir gecikme döngüsüyle LED sayacı; üçüncü testte bir **fonksiyon
> çağrısı** ve **butona göre** değişen davranış — yani giriş/çıkış birimlerini de
> kullanıyoruz. Resete basınca loader yeniden devreye girip yeni program bekliyor."

### [2:35–3:10] SAHNE 5 — Özgünlük #2: sentezden önce doğrulama (ISS)
**Ekran:** `python loader/test_loader.py` çıktısı (3 satır OK), yanında `fig_fsm` diyagramı.
**Anlatım:**
> "Peki bu sistemin doğruluğunu nasıl garanti ettik? Donanım hatalarını avlamak yavaştır.
> Bu yüzden **kendi RV32I komut-set simülatörümüzü** yazdık ve loader'ın **gerçek makine
> kodunu** sentezden önce çalıştırdık. Simülatör, host'un paketlerini loader'a verdi;
> loader programı doğru adrese **bayt-bayt** yazdı, her bloğu ACK'ledi ve doğru adrese
> atladı. ACK alınması şu anlama gelir: **loader'ın CRC'si, host'un CRC'siyle birebir
> aynı** — uyuşmasaydı her paket reddedilirdi. Bozuk paket enjekte ettiğimizde de loader
> NAK verip yeniden gönderimle toparladı."

### [3:10–3:40] SAHNE 6 — Mühendislik derinliği: gerçek bir hata ve çözümü
**Ekran:** `bram.v` içindeki `\`include "mem_init.vh"` satırı + `mem_init.vh` içeriği.
**Anlatım:**
> "Yol boyunca gerçek sistem-seviyesi sorunlarla karşılaştık. Örneğin: sentez aracı,
> belleği başlatan standart `$readmemh` komutunu **sessizce yok sayıyordu** — program
> belleğe hiç yüklenmiyordu. Çözümümüz: araç zincirimizi, belleği dolduran açık Verilog
> deyimleri üreten bir başlık dosyası üretecek şekilde genişlettik ve bunu donanıma
> `include` ettik. Böylece yazılım ile donanım arasında sağlam bir köprü kurduk."

*(Alternatif/ek hikâye: "CRC-16 için gereken XOR komutu setimizde yoktu; assembler'ımıza
XOR, XORI ve LBU komutlarını ekledik." — Süre kalırsa.)*

### [3:40–4:10] SAHNE 7 — Sürdürülebilirlik ve etki
**Ekran:** Sade bir metin kartı (3 madde) veya konuşan kişi.
**Anlatım:**
> "Bu projenin teknik ötesinde bir anlamı da var. **Açık kaynaklı RISC-V** kullanmak,
> lisans bağımlılığı olmadan yerli ve özgün araç zinciri geliştirmenin mümkün olduğunu
> gösterir. Loader üzerinden **uzaktan güncellenebilirlik**, bir cihazı değiştirmek yerine
> yazılımını yenilemeyi sağlar — bu da elektronik atığı azaltır. Sade çekirdek ve
> optimize yazılım, daha düşük güç tüketimi, yani daha küçük karbon ayak izi demektir."

### [4:10–4:35] SAHNE 8 — Sonuç
**Ekran:** `fig_arch` diyagramı tekrar; üzerine "kaynak → assembler → linker → loader →
UART → RAM → çalışan program" akışı vurgulanır.
**Anlatım:**
> "Özetle: kaynak koddan fiziksel donanımda çalışan programa uzanan **tüm zinciri kendimiz
> kurduk** ve her halkayı kanıtladık. Assembler, linker, hata kontrollü bir UART
> protokolü, işlemcinin kendi dilinde bir bootstrap loader, ve bunları doğrulayan bir
> simülatör — hepsi bir arada, gerçek bir FPGA üzerinde."

### [4:35–4:50] SAHNE 9 — Kapanış kartı
**Ekran:** Kapanış kartı: grup üyeleri + ders + "Teşekkürler". (İsteğe bağlı: repo linki.)
**Anlatım:**
> "İzlediğiniz için teşekkürler."

---

## 3) Bireysel konuşma dağılımı (PÇ12 — her üye görünür olmalı)

Her üye en az bir sahnenin anlatımını üstlensin (özgeçmiş için yüz/ses görünürlüğü değerli):
- **Üye 1:** Sahne 2 (mimari) + Sahne 8 (sonuç)
- **Üye 2:** Sahne 3 (loader/toolchain) + Sahne 5 (ISS doğrulama)
- **Üye 3:** Sahne 4 (canlı demo) + Sahne 6 (hata/çözüm) + Sahne 7 (sürdürülebilirlik)

> Sunumda hoca bireysel soru soracağı için, herkes kendi anlattığı bölümü **derinlemesine**
> bilmeli (bkz. raporun Bireysel Katkı Beyanı bölümü).

---

## 4) Canlı demo için kopyala-çalıştır komutları (akıcı çekim)

`assembler_1/assembler_1/` dizininde:
```
# (1) Uygulamayı derle
python run_link.py apps/t1_arith_led.s -T apps/app.ld -o apps/t1_arith_led -v

# (2) FPGA'ya yükle (COM numaranı kendi portunla değiştir)
cd host
python host_loader.py --port COM5 --baud 9600 --bin ../apps/t1_arith_led.bin --addr 0x3000 --entry 0x3000 -v

# (3) Diğer testler
python host_loader.py --port COM5 --baud 9600 --bin ../apps/t2_loop_blink.bin  --addr 0x3000 --entry 0x3000
python host_loader.py --port COM5 --baud 9600 --bin ../apps/t3_func_button.bin --addr 0x3000 --entry 0x3000

# (Opsiyonel kanıt) Sentez öncesi ISS doğrulaması
cd ..
python loader/test_loader.py
```
Her yükleme öncesi **karta reset** (S2) bas → loader yeniden paket beklemeye başlar.

**Ekranda işaret edeceğin "kanıt" sayıları:** ACK = `0x06`, LED = `42` = `0b101010`,
loader = `328 B / 82 komut`, CRC kontrol değeri = `0x29B1`.

---

## 5) Kalite / prodüksiyon kontrol listesi (özgeçmiş seviyesi)

- [ ] **Açılış + kapanış kartı** (tutarlı renk; raporun lacivert tonu #1F3864 ile uyumlu).
- [ ] **Lower-third** (alt bant): konuşanın adı + rolü ilk göründüğünde.
- [ ] **Altyazı** (Türkçe; özgeçmiş için ek İngilizce altyazı = büyük artı).
- [ ] **Net ses** (gürültü yok, tutarlı seviye). Kötü ses = kötü video.
- [ ] **Ekran yazıları okunur** (terminal/kod fontu büyük; 1080p).
- [ ] **Tempo:** sahneler arası sert kesme; ölü an yok. Komut beklemeleri hızlandır.
- [ ] **Diyagramlar** kullan (fig_arch, fig_fsm) — saf ekran kaydından daha "anlatımlı".
- [ ] **Süre ≤ 5:00** (hedef 4:30–4:55). Sona doğru hızlan, sarkma.
- [ ] **Müzik** (hafif, telifsiz, düşük seviye) — konuşmayı bastırmasın.
- [ ] LED/kart çekimi **net ve sabit** (titreme yok; tripod veya sabit zemin).

---

## 6) Yapılacaklar / Yapılmayacaklar

**Yap:**
- "Neden böyle yaptık" anlat (tasarım kararı), sadece "ne yaptık" değil.
- En az bir **kanıt anı** göster (ACK akışı, LED=42, ISS testi).
- Özgünlük 4 maddesinden en az 3'ünü açıkça söyle.
- Sürdürülebilirliği kısa ama somut bağla (RISC-V açıklığı, OTA/e-atık).

**Yapma:**
- 5 dakikayı aşma.
- Sadece LED'i gösterip "çalışıyor" deyip geçme (hoca bunu istemiyor).
- 115200 baud'u canlı deneme (çalışmıyor).
- Okunmayan küçük font / gürültülü ses / dağınık masaüstü.

---

## 7) Teslim

- **Süre:** ≤ 5 dk. **Format:** MP4, 1080p.
- **Dosya adı:** `BIL302_PROJE3_VIDEO_A.XX_B.YY_C.ZZ_170526.MP4`
  *(şablonda "PROJE1 VIDEO" yazıyor — büyük olasılıkla kopya hatası; LMS/hocaya **PROJE3**
  olarak teyit et.)*
- **Yükleme:** lms.subu.edu.tr, 07.06.2026 23:59'a kadar.

---

## 8) 30 saniyelik "asansör" versiyonu (sunum açılışı veya kısa tanıtım için)

> "RISC-V tabanlı bir işlemci için assembler, linker ve işlemcinin kendi komut setiyle
> yazılmış bir bootstrap loader geliştirdik. Bilgisayardan UART üzerinden, CRC-16 ile
> korunan paketlerle program gönderiyor; FPGA'daki loader bunu belleğe yazıp çalıştırıyor.
> En özgün yanı: bunu sentezden önce kendi yazdığımız bir komut-set simülatöründe
> doğruladık ve sonra Tang Nano 9K üzerinde fiziksel olarak çalıştırdık."
