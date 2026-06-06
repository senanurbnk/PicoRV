// BIL302 Proje 3 raporu — Courier New 10pt akademik rapor uretici (docx-js)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, Header, Footer, PageBreak, TableOfContents, ImageRun,
} = require("docx");
const path = require("path");

const FONT = "Courier New";
const SZ = 20;        // 10pt (half-points)
const SZ_SMALL = 18;  // 9pt for dense tables/code
const ACCENT = "1F3864";

// ---- helpers ----
function R(text, o = {}) {
  return new TextRun({ text, font: FONT, size: o.size || SZ, bold: o.bold || false,
    italics: o.italics || false, color: o.color, highlight: o.highlight });
}
function P(runs, o = {}) {
  const children = Array.isArray(runs) ? runs : [R(runs, o)];
  return new Paragraph({ children, spacing: { after: o.after == null ? 120 : o.after,
    before: o.before || 0, line: o.line || 264 }, alignment: o.align,
    border: o.border, pageBreakBefore: o.pageBreakBefore || false });
}
// placeholder (sari highlight) — kullanici dolduracak
function PH(text) { return R(text, { highlight: "yellow", bold: true }); }
function H1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1,
    children: [R(text, { bold: true, size: 26 })],
    spacing: { before: 280, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 2 } } });
}
function H2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2,
    children: [R(text, { bold: true, size: 22 })], spacing: { before: 200, after: 120 } });
}
function H3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3,
    children: [R(text, { bold: true, size: 20 })], spacing: { before: 140, after: 80 } });
}
// monospace blok (ASCII sema / kod) — her satir ayri paragraf, sik aralik
function MONO(block, o = {}) {
  const lines = block.replace(/\t/g, "    ").split("\n");
  return lines.map((ln, i) =>
    new Paragraph({ children: [R(ln.length ? ln : " ", { size: o.size || SZ_SMALL })],
      spacing: { after: 0, line: 230 },
      shading: { type: ShadingType.CLEAR, fill: "F2F2F2" } }));
}
function IMG(file, w, h, caption) {
  const data = fs.readFileSync(path.join(__dirname, "img", file));
  const out = [ new Paragraph({ alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 40 },
    children: [ new ImageRun({ type: "png", data, transformation: { width: w, height: h },
      altText: { title: caption || file, description: caption || file, name: file } }) ] }) ];
  if (caption) out.push(CAP(caption));
  return out;
}
function CAP(text) { // sekil/tablo basligi
  return P([R(text, { italics: true, size: SZ_SMALL, color: "595959" })],
    { align: AlignmentType.CENTER, after: 160 });
}
const BORD = { style: BorderStyle.SINGLE, size: 1, color: "BFBFBF" };
const BORDERS = { top: BORD, bottom: BORD, left: BORD, right: BORD,
  insideHorizontal: BORD, insideVertical: BORD };
function cell(text, w, o = {}) {
  const runs = Array.isArray(text) ? text
    : [R(String(text), { bold: o.bold, size: o.size || SZ_SMALL })];
  return new TableCell({ width: { size: w, type: WidthType.DXA }, borders: BORDERS,
    shading: o.fill ? { type: ShadingType.CLEAR, fill: o.fill } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ children: runs, spacing: { after: 0, line: 230 },
      alignment: o.align })] });
}
function TABLE(widths, rows) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0,
      children: r.map((c, ci) => cell(c, widths[ci],
        { bold: ri === 0, fill: ri === 0 ? "D9E2F3" : undefined })) })) });
}
function BULLET(text) {
  return new Paragraph({ numbering: { reference: "b", level: 0 },
    children: Array.isArray(text) ? text : [R(text)], spacing: { after: 80, line: 264 } });
}

const CW = 9360; // content width (US Letter, 1" margins)

// ================= CONTENT =================
const body = [];

// ---- TITLE PAGE ----
body.push(P([R("BIL302 — SİSTEM PROGRAMLAMA", { bold: true, size: 24 })],
  { align: AlignmentType.CENTER, before: 1200, after: 80 }));
body.push(P([R("3. PROJE / TASARIM RAPORU", { bold: true, size: 22 })],
  { align: AlignmentType.CENTER, after: 600 }));
body.push(P([R("PicoRV İşlemci Alt Kümesi (RV32I) için", { bold: true, size: 28 })],
  { align: AlignmentType.CENTER, after: 60 }));
body.push(P([R("FPGA Tabanlı Loader Tasarımı", { bold: true, size: 28 })],
  { align: AlignmentType.CENTER, after: 600 }));
body.push(P([R("Hedef Donanım: Sipeed Tang Nano 9K (Gowin GW1NR-9)", {})],
  { align: AlignmentType.CENTER, after: 40 }));
body.push(P([R("Çekirdek: PicoRV32 (RV32I) — Araç zinciri: Özgün Python toolchain", {})],
  { align: AlignmentType.CENTER, after: 600 }));
body.push(P([R("Grup Üyeleri:", { bold: true })], { align: AlignmentType.CENTER, after: 40 }));
body.push(P([PH("[Ad Soyad — Öğrenci No]"), R("   ")], { align: AlignmentType.CENTER, after: 20 }));
body.push(P([PH("[Ad Soyad — Öğrenci No]")], { align: AlignmentType.CENTER, after: 20 }));
body.push(P([PH("[Ad Soyad — Öğrenci No]")], { align: AlignmentType.CENTER, after: 400 }));
body.push(P([R("Haziran 2026", {})], { align: AlignmentType.CENTER, after: 0 }));
body.push(new Paragraph({ children: [new PageBreak()] }));

// ---- TOC ----
body.push(P([R("İÇİNDEKİLER", { bold: true, size: 24 })], { after: 160 }));
body.push(new TableOfContents("İçindekiler", { hyperlink: true, headingStyleRange: "1-2" }));
body.push(new Paragraph({ children: [new PageBreak()] }));

// ---- ÖZET ----
body.push(H1("ÖZET"));
body.push(P("Bu projede, daha önce geliştirilen assembler (1. proje) ve linker (2. proje) " +
  "modüllerinin üzerine, FPGA donanımı üzerinde çalışan özgün bir yükleyici (bootstrap " +
  "loader) sistem yazılımı inşa edilmiştir. Loader, PicoRV32 işlemcisinin kendi RV32I " +
  "komut setiyle yazılmış ve yine bu projede geliştirilen assembler+linker ile " +
  "derlenmiştir. Bilgisayar (host) tarafında çalışan bir Python uygulaması, linker " +
  "çıktısı .bin dosyasını CRC-16/CCITT ile korunan paketler hâlinde UART üzerinden " +
  "gönderir; FPGA üzerindeki loader bu paketleri alır, doğrular, uygulamayı RAM'e yazar " +
  "ve programın giriş adresine atlayarak kodu fiziksel olarak çalıştırır. Sistem, " +
  "sentezden önce özgün bir RV32I komut-set simülatörü (ISS) üzerinde gerçek makine kodu " +
  "çalıştırılarak doğrulanmış, ardından Sipeed Tang Nano 9K kartı üzerinde fiziksel " +
  "olarak başarıyla çalıştırılmıştır. Üç farklı karmaşıklıkta Assembly test programı " +
  "(aritmetik, döngü, fonksiyon çağrısı + buton girişi) ile sistemin doğruluğu ve " +
  "kararlılığı kanıtlanmıştır."));

// ================= 1. GIRIS =================
body.push(H1("1. GİRİŞ VE LİTERATÜR ARAŞTIRMASI"));
body.push(P("Modern gömülü sistemlerde, derlenmiş makine kodunun hedef donanımın belleğine " +
  "yerleştirilip çalıştırılması bir yükleyici (loader) yazılımının sorumluluğundadır. Bu " +
  "proje, kaynak koddan fiziksel donanımda çalışan programa uzanan uçtan uca bir araç " +
  "zinciri (toolchain) kurarak, bilgisayar mimarisi teorisini somut bir donanım-yazılım " +
  "ortak tasarımı (co-design) deneyimine dönüştürmeyi amaçlar. Karşılaşılan tasarım " +
  "kararları, deneme-yanılma yerine uluslararası standartlar ve akademik literatür " +
  "taranarak verilmiştir (PÇ6)."));

body.push(H2("1.1. Gömülü Sistemlerde Program Yükleme Mimarileri"));
body.push(P("Bir bootloader, ana programdan önce çalışan ve uygulama kodunu bir kaynaktan " +
  "okuyarak çalıştırılabilir belleğe yerleştiren küçük bir sistem yazılımıdır. Beck'in " +
  "sistem yazılımı modelinde tarif edilen bootstrap loader, nesne kodunu bir aygıttan " +
  "okuyup belleğe yazan ve ardından yüklenen programın başlangıç adresine dallanan bir " +
  "yapıdır; bu proje bu klasik modelin modern bir karşılığıdır (cihaz = UART, hedef = " +
  "RAM 0x3000, dallanma = JALR) [4] (PÇ6). Gömülü sistemlerde kod aktarımı için yaygın " +
  "üç fiziksel arayüz öne çıkar; karşılaştırmaları Tablo 1.1'de verilmiştir."));
body.push(TABLE([1500, 2600, 2600, 2660], [
  ["Arayüz", "Avantaj", "Dezavantaj", "Tipik kullanım"],
  ["UART", "Basit, 2 hat, USB-seri köprü ile PC'ye doğrudan", "Düşük hız (≈115 kbps)", "Bootloader, hata ayıklama"],
  ["SPI", "Yüksek hız, flash XIP", "Daha çok hat, master/slave", "Flash'tan boot"],
  ["JTAG", "Doğrudan donanım erişimi, debug", "Özel donanım/protokol", "Üretim programlama, debug"],
]));
body.push(CAP("Tablo 1.1. Gömülü sistemlerde yaygın program yükleme arayüzleri."));
body.push(P("Bu projede UART seçilmiştir: Tang Nano 9K kartında BL702 tabanlı bir USB-UART " +
  "köprüsü hazır bulunur, ek donanım gerektirmez ve ders kapsamındaki bootstrap loader " +
  "modeline en uygun, en sade arayüzdür. Yükleyici, donanımsal bir durum makinesi yerine " +
  "PicoRV32 üzerinde koşan bir yazılım programı olarak tasarlanmıştır; bu karar hem " +
  "dersin hedefiyle (\"loader işlemcinin kendi komut setiyle yazılacak\") hem de araç " +
  "zincirinin ikinci kez, sistem-yazılımı seviyesinde kanıtlanması ilkesiyle uyumludur " +
  "[1][2] (PÇ6)."));

body.push(H2("1.2. Seri Haberleşme ve Veri Doğrulama Protokolleri"));
body.push(P("Seri hat üzerinden kod aktarımında bit hataları programın bozulmasına yol açar; " +
  "bu nedenle her paket bir hata kontrol koduyla korunmalıdır. İki temel yaklaşım " +
  "karşılaştırılmıştır (Tablo 1.2). Basit toplama tabanlı sağlama toplamı (checksum) " +
  "hesaplama açısından ucuzdur ancak bit yer değiştirmeleri ve çift hatalara karşı zayıftır. " +
  "Döngüsel artıklık denetimi (CRC), polinom bölmesi temelli olduğundan ardışık (burst) " +
  "hataları çok daha güçlü yakalar [3] (PÇ6)."));
body.push(TABLE([2200, 3580, 3580], [
  ["Yöntem", "Güç", "Maliyet / Not"],
  ["Checksum (toplama)", "Tek-bit hata zayıf; burst zayıf", "Çok ucuz; yetersiz güvenilirlik"],
  ["CRC-16/CCITT", "16-bit'e kadar burst hatayı kesin yakalar", "Bit/tablo döngüsü; standart (ITU-T V.41)"],
]));
body.push(CAP("Tablo 1.2. Hata kontrol yöntemlerinin karşılaştırması."));
body.push(P("Bu projede CRC-16/CCITT-FALSE (polinom 0x1021, başlangıç 0xFFFF, yansımasız/" +
  "MSB-first) seçilmiştir. Yansımasız MSB-first biçim tercih edilmiştir; çünkü bu biçim " +
  "PicoRV32 üzerinde RV32I komutlarıyla (sola kaydır, en yüksek biti test et, koşullu " +
  "XOR 0x1021) birebir ve verimli yazılabilir. Algoritmanın doğruluğu standart kontrol " +
  "değeri ile sınanmıştır: \"123456789\" dizisinin CRC değeri 0x29B1 olarak elde " +
  "edilmiştir [3][5] (PÇ6, PÇ7). Aynı CRC algoritması hem host (Python) hem loader " +
  "(RV32I) tarafında birebir uygulanmıştır."));
body.push(P([R("Atıf kriteri: ", { bold: true }),
  R("Raporda resmî RISC-V ISA dökümanı [1], PicoRV32 çekirdeği [2], CRC polinom seçimi " +
  "üzerine IEEE/IFIP DSN makalesi [3], Beck'in sistem yazılımı kaynağı [4] ve ITU-T V.41 " +
  "standardı [5] dâhil en az beş akademik/standart kaynağa atıf yapılmıştır (PÇ6).")]));

// ================= 2. SISTEM MIMARISI =================
body.push(H1("2. SİSTEM MİMARİSİ VE DONANIM-YAZILIM ORTAK TASARIMI (CO-DESIGN)"));
body.push(P("Sistem, bilgisayar tarafında çalışan bir yazılım zinciri ile FPGA tarafında " +
  "çalışan bir SoC'tan (System-on-Chip) oluşur. Genel mimari ve veri akışı Şekil 2.1'de " +
  "verilmiştir."));
body.push(...IMG("fig_arch.png", 624, 380, "Şekil 2.1. Uçtan uca sistem mimarisi ve veri akışı (Co-Design)."));

body.push(H2("2.1. Toolchain Arayüz Standartları"));
body.push(P("Araç zinciri modülleri arasındaki veri alışverişi, açıkça tanımlanmış dosya ve " +
  "protokol formatları üzerinden yürür (PÇ6). Assembler, her kaynak dosyayı PICORV-OBJ " +
  "adını verdiğimiz, JSON tabanlı özgün bir nesne formatına (.o.json) çevirir; bu format " +
  "section'ları (.text/.data), sembol tablosunu (LOCAL/GLOBAL, tanımlı/harici) ve " +
  "relocation kayıtlarını içerir. JSON tercih edilmiştir çünkü hata ayıklanabilir ve " +
  "gözle doğrulanabilir. Linker, bir veya daha çok .o.json dosyasını birleştirip düz " +
  "bellek imajı üretir ve bunu üç biçimde dışa verir: ham ikili (.bin), Verilog " +
  "$readmemh (.hex) ve Verilog include başlığı (_init.vh)."));
body.push(P("Host ile loader arasındaki haberleşme, Tablo 2.1'deki paket çerçevesiyle " +
  "yapılır. CRC, SYNC hariç CMD..DATA alanları üzerinden hesaplanır."));
body.push(...IMG("fig_packet.png", 624, 139, "Şekil 2.2. Host–loader paket çerçevesi (CMD: 0x01=WRITE_BLOCK, 0x02=START, 0x03=PING; yanıt 0x06=ACK / 0x15=NAK)."));

body.push(H2("2.2. FPGA Loader ve PicoRV32 Bellek Haritası"));
body.push(P("SoC'un adres çözücüsü, 32-bit adresin üst yarım baytına (mem_addr[31:28]) göre " +
  "üç bölgeyi ayırır. Bellek haritası Tablo 2.2'de verilmiştir. BRAM, 2. projedeki 8 " +
  "KB'tan 16 KB'a çıkarılmıştır; böylece loader (0x0000) ve uygulama (0x3000) aynı fiziksel " +
  "bellekte ayrık durur ve loader uygulamayı yazarken kendi kod bölgesini ezmez."));
body.push(TABLE([2700, 2200, 4460], [
  ["Adres", "Aygıt", "İçerik"],
  ["0x0000_0000–0x0000_0FFF", "BRAM", "Loader (.text); sentezde gömülü, PROGADDR_RESET"],
  ["0x0000_3000–0x0000_3FFF", "BRAM", "Uygulama; UART'tan runtime yüklenir, entry=0x3000"],
  ["0x1000_0000", "GPIO", "+0x00 LED çıkış (6 bit), +0x04 buton giriş"],
  ["0x2000_0000", "UART", "+0x00 DATA, +0x04 STATUS (rx_valid, tx_busy)"],
]));
body.push(CAP("Tablo 2.2. PicoRV32 SoC bellek haritası."));
body.push(P("Loader'ın iç işleyişi bir sonlu durum makinesidir (FSM); UART'tan paket alırken " +
  "uygulama henüz başlatılmamıştır (\"bekleme\" durumu), yükleme bitince START komutuyla " +
  "uygulamanın giriş adresine JALR ile atlanır (bu, işlemcinin reset hattını serbest " +
  "bırakmanın yazılımsal karşılığıdır). FSM Şekil 2.3'te verilmiştir."));
body.push(...IMG("fig_fsm.png", 450, 516, "Şekil 2.3. Loader sonlu durum makinesi (FSM)."));
body.push(P("Loader, RV32I komutlarıyla yazılmış 82 komutluk (328 bayt) tek dosyalık bir " +
  "programdır. getc/putc/crc16_byte alt programları yaprak (leaf) niteliktedir; başka alt " +
  "program çağırmadıkları için tek seviye dönüş adresi (ra) yeterlidir ve yığın (stack) " +
  "gerekmez. Kalıcı durum, saklı registerlarda tutulur (Tablo 2.3)."));
body.push(TABLE([1400, 3280, 1400, 3280], [
  ["Reg", "Anlam", "Reg", "Anlam"],
  ["s0", "UART taban adresi", "s4", "hedef/entry adresi"],
  ["s1", "çalışan CRC", "s5", "gelen CRC"],
  ["s2", "komut (CMD)", "s6", "sayaç i"],
  ["s3", "uzunluk (LEN)", "s7", "yazma işaretçisi"],
]));
body.push(CAP("Tablo 2.3. Loader register tahsisi."));

// ================= 3. DENEYSEL =================
body.push(H1("3. DENEYSEL ÇALIŞMALAR, TEST VE ANALİZ"));
body.push(P("Sistemin yalnızca çalıştığını söylemek yeterli değildir; doğruluğu sistematik " +
  "bir deney metodolojisiyle kanıtlanmıştır. Donanım sentezi pahalı ve yavaş olduğundan, " +
  "önce yazılım katmanları FPGA'sız doğrulanmış, ardından fiziksel donanımda " +
  "çalıştırılmıştır (PÇ7)."));

body.push(H2("3.1. Deney Tasarımı ve Test Senaryoları"));
body.push(P("Doğrulama metodolojisinin merkezinde, bu proje için yazılan özgün bir RV32I " +
  "komut-set simülatörü (ISS) bulunur. ISS, linker'ın ürettiği gerçek makine kodunu " +
  "çalıştırır ve UART/GPIO çevre birimlerini modelleyerek loader'ın davranışını sentez " +
  "olmadan birebir test etmeyi sağlar. Loader'ın gerçek ikili çıktısı, host'un ürettiği " +
  "paketlerle beslenmiş; uygulamayı 0x3000'e bayt-tam (endianness dâhil) yazdığı, her " +
  "bloğu ACK'lediği (yani loader CRC'sinin host CRC'si ile birebir olduğu; aksi hâlde her " +
  "blok NAK olurdu), uygulamaya atladığı ve hatalı CRC'de NAK→yeniden gönderme yolunun " +
  "çalıştığı kanıtlanmıştır (PÇ7). Test matrisi Tablo 3.1'de özetlenmiştir."));
body.push(TABLE([2200, 3400, 3760], [
  ["Test", "Doğruladığı", "Sonuç"],
  ["ISS: load+jump", "Paket→RAM yazımı, jump", "RAM bayt-tam, pc→0x3000 ✓"],
  ["ISS: app çalıştı", "Jump sonrası uygulama", "LED = 42 (0b101010) ✓"],
  ["ISS: bozuk CRC", "NAK + retransmit", "NAK sonra ACK, RAM doğru ✓"],
  ["UART FSM modeli", "8N1 TX/RX bit zamanlama", "0x00/FF/AA/55 birebir ✓"],
  ["Negatif: undef ref", "Linker hata yönetimi", "\"undefined reference\" ✓"],
  ["Negatif: çoklu tanım", "Linker hata yönetimi", "\"multiple definition\" ✓"],
  ["Fiziksel: Tang Nano 9K", "Tüm sistem", "Echo + loader + T1/T2/T3 ✓"],
]));
body.push(CAP("Tablo 3.1. Doğrulama test matrisi."));
body.push(P("Şablonun gereği uyarınca, FPGA'nın giriş/çıkış imkânlarını (LED çıkışı, buton " +
  "girişi) kullanan, artan karmaşıklıkta üç Assembly test programı hazırlanmıştır (PÇ7). " +
  "Programlar loader tarafından UART üzerinden yüklenip çalıştırılmıştır."));

body.push(H3("Test 1 — Aritmetik ve LED çıkışı (en basit yükleme kanıtı)"));
body.push(...MONO(
`_start:
    LUI   t0, 0x10000     # GPIO/LED taban adresi
    LI    t1, 40
    LI    t2, 2
    ADD   t3, t1, t2      # 40 + 2 = 42
    SW    t3, 0(t0)       # LED = 42 = 0b101010
spin:
    J     spin`));
body.push(CAP("Şekil 3.1. T1 — 24 bayt / 6 komut. Sonuç: LED deseni 0b101010."));

body.push(H3("Test 2 — Döngü ve zamanlama (LED sayaç/blink)"));
body.push(...MONO(
`_start:
    LUI   t0, 0x10000
    LI    t1, 0
loop:
    ANDI  t2, t1, 0x3F   # alt 6 bit -> LED
    SW    t2, 0(t0)
    ADDI  t1, t1, 1      # sayac++
    LUI   t3, 0x8        # gecikme (artir -> yavas blink)
delay:
    ADDI  t3, t3, -1
    BNE   t3, x0, delay
    J     loop`));
body.push(CAP("Şekil 3.2. T2 — 36 bayt / 9 komut. Döngü, dallanma (BNE/J) ve zamanlama."));

body.push(H3("Test 3 — Fonksiyon çağrısı ve buton girişi (en karmaşık)"));
body.push(...MONO(
`_start:
    LUI   s0, 0x10000        # GPIO taban
main:
    CALL  get_button         # alt program: a0 = buton (0/1)
    BEQ   a0, x0, released
    LI    t1, 0x3F           # basili -> 6 LED
    J     show
released:
    LI    t1, 0x09           # birakildi -> 0b001001
show:
    SW    t1, 0(s0)
    J     main
get_button:                  # yaprak alt program
    LW    a0, 4(s0)          # GPIO+4 = buton
    ANDI  a0, a0, 1
    RET`));
body.push(CAP("Şekil 3.3. T3 — 44 bayt / 11 komut. JAL/JALR alt program, GPIO girişi, koşullu dallanma."));

body.push(H3("3.1.1. Karşılaşılan Sorunlar ve Sinyal/Sistem Seviyesi Analiz"));
body.push(P("Geliştirme sürecinde öğretici sorunlarla karşılaşılmış ve her biri kök neden " +
  "analiziyle çözülmüştür (PÇ7):"));
body.push(BULLET("Komut seti eksiği: CRC-16 temelde XOR gerektirir; mevcut 20 komutluk sette " +
  "XOR yoktu. Çözüm: assembler'a XOR, XORI ve LBU komutları eklenerek alt küme 23 komuta " +
  "çıkarıldı; relocation mantığı değişmedi."));
body.push(BULLET("Endianness riski: PicoRV32 little-endian'dır; host bayt sırası ile " +
  "loader'ın SB yazımının uyuşmaması programı bozar. Bu risk, sentezden önce ISS'te RAM " +
  "geri-okuması ile kesin olarak elenmiştir."));
body.push(BULLET("$readmemh'in Gowin tarafından sessizce yok sayılması: BRAM sıfır kalıyor, " +
  "CPU NOP koşuyordu. Çözüm: araç zinciri, header-guard'lı explicit mem[i]=32'h...; " +
  "deyimlerinden oluşan bir _init.vh üretip bram.v'ye include ettirmiştir."));
body.push(BULLET("Bank besleme gerilimi çakışması (CT1136): LED/buton Bank3'te 1.8V " +
  "beslemelidir; LVCMOS33 ile çakışır. Çözüm: ilgili pinler LVCMOS18 yapılmıştır."));
body.push(BULLET("Adres çözücü çakışması: tasarımın ilk hâlindeki MMIO adresleri kaba " +
  "([31:28]) çözücüde BRAM'e düşüyordu; GPIO 0x1, UART 0x2 olacak şekilde yeniden " +
  "düzenlenmiş, çalışan SoC bozulmamıştır."));

body.push(H2("3.2. Veri Toplama ve Donanım Metrikleri"));
body.push(P("Üretilen makine kodu boyutları Tablo 3.2'de verilmiştir (gerçek artefaktlardan)."));
body.push(TABLE([3120, 2120, 4120], [
  ["Modül", "Boyut", "Açıklama"],
  ["loader.bin", "328 B / 82 komut", "Boot bölgesine gömülü RV32I loader"],
  ["echo (bring-up)", "44 B / 11 komut", "UART donanım doğrulama firmware'i"],
  ["t1_arith_led", "24 B / 6 komut", "Aritmetik + LED"],
  ["t2_loop_blink", "36 B / 9 komut", "Döngü + sayaç"],
  ["t3_func_button", "44 B / 11 komut", "Fonksiyon + buton"],
]));
body.push(CAP("Tablo 3.2. Kod boyutu metrikleri."));
body.push(P("Yükleme süresi, paket boyutu ve baud hızıyla doğrusal ilişkilidir. Teorik " +
  "tahmin: süre ≈ (toplam_bayt × 10 bit) / baud + ACK gecikmeleri. Aşağıdaki tablo board " +
  "üzerinde host_loader.py'nin zaman damgalarıyla ölçülerek doldurulacaktır (PÇ7)."));
body.push(TABLE([2600, 2380, 2380, 2000], [
  ["Kod boyutu", "Süre @9600", "Süre @115200", "Açıklama"],
  ["64 B", PH_cell(), PH_cell(), "ölçüm"],
  ["256 B", PH_cell(), PH_cell(), "ölçüm"],
  ["1 KB", PH_cell(), PH_cell(), "ölçüm"],
]));
body.push(CAP("Tablo 3.3. Yükleme süresi vs kod boyutu (board ölçümleriyle doldurulacak)."));
body.push(P([R("FPGA kaynak tüketimi (Gowin sentez + Place&Route raporundan): ", {}),
  PH("[LUT: __ / 8640, Register/FF: __ / 6480, BSRAM: __ / 26 blok, Fmax: __ MHz]"),
  R(". Bu değerler Gowin IDE'nin sentez raporundan alınarak yazılacaktır. Loader + UART + " +
  "GPIO + 16 KB BRAM içeren tam SoC, GW1NR-9'un kapasitesinin küçük bir kısmını kullanır " +
  "(PÇ7).")]));
body.push(P("Analiz: Yükleme süresinin temel darboğazı UART baud hızıdır; 9600'den " +
  "115200'e geçiş yükleme süresini yaklaşık 12 kat kısaltır. Loader'ın kendisi (328 bayt) " +
  "bitstream'e gömülü olduğundan yükleme süresine dâhil değildir; yalnızca uygulama " +
  "kodunun boyutu belirleyicidir (PÇ7)."));

// ================= 4. ETKILER =================
body.push(H1("4. PROJENİN KÜRESEL, TOPLUMSAL VE EKONOMİK ETKİLERİ"));
body.push(H2("4.1. Sürdürülebilirlik ve Yeşil Bilişim (Green Computing)"));
body.push(P("RISC-V gibi sade ve açık bir komut seti mimarisi, gereksiz donanım bloklarından " +
  "kaçınarak daha az transistör ve dolayısıyla daha düşük güç tüketimi sağlar. Bu projede " +
  "kullanılan PicoRV32, FPGA'nın yalnızca küçük bir bölümünü kullanan, boyut için " +
  "optimize edilmiş bir çekirdektir; gömülü cihazlarda enerji verimliliği doğrudan karbon " +
  "ayak izini düşürür. Ayrıca yazılım optimizasyonu (örneğin loader'ın yığın kullanmayan, " +
  "yaprak alt programlardan oluşan tasarımı) bellek ve çevrim sayısını azaltarak enerji " +
  "tasarrufuna katkı sağlar; bu, SKA 7 (Erişilebilir ve Temiz Enerji) ve SKA 13 (İklim " +
  "Eylemi) hedefleriyle uyumludur (PÇ8)."));
body.push(H2("4.2. Ekonomik Sürdürülebilirlik ve Teknolojik Bağımsızlık"));
body.push(P("Ticari ve kapalı kaynaklı işlemci mimarilerine (ör. lisans ücretli ISA'lar) " +
  "kıyasla, açık kaynaklı RISC-V ekosistemi lisans maliyeti olmadan özgün araç zinciri ve " +
  "işlemci geliştirmeye olanak tanır. Bu projede assembler, linker ve loader'ın tamamen " +
  "kendi imkânlarımızla yazılması, bir kurumun veya ülkenin dış bağımlılık olmadan kendi " +
  "çip araç zincirini kurabileceğini somut olarak göstermektedir. Bu durum Ar-Ge " +
  "maliyetlerini düşürür ve yerli yarı iletken endüstrisinin gelişimine zemin hazırlar; " +
  "SKA 8 (İnsana Yakışır İş ve Ekonomik Büyüme) ve SKA 9 (Sanayi, Yenilikçilik ve " +
  "Altyapı) ile ilişkilidir (PÇ8)."));
body.push(H2("4.3. Fonksiyonel Güvenlik ve Sağlık"));
body.push(P("CRC-16 ile veri bütünlüğünü güvence altına alan bir yükleme mekanizması, " +
  "yazılım güncellemesi sırasında bozuk kod yüklenmesini engeller. Tıbbi cihazlar, " +
  "otomotiv (ör. ECU yazılımı) ve savunma gibi kritik gömülü sistemlerde bozuk bir " +
  "güncelleme can güvenliğini tehdit edebilir. Bu projede gösterilen hata kontrollü " +
  "(ACK/NAK + retransmit) loader yaklaşımı, bu tür sistemlerde güvenilirliğin temel " +
  "yapı taşıdır; SKA 3 (Sağlık ve Kaliteli Yaşam) ile ilişkilidir (PÇ8)."));
body.push(H2("4.4. E-Atık Yönetimi ve Döngüsel Ekonomi"));
body.push(P("FPGA tabanlı ve loader üzerinden uzaktan güncellenebilen (OTA) bir sistem, " +
  "donanımın yazılımsal olarak yeniden yapılandırılmasına imkân verir. Bir cihazın " +
  "işlevini değiştirmek için donanımı çöpe atmak yerine yeni kod yüklemek yeterlidir; bu, " +
  "cihaz ömrünü uzatır ve elektronik atığı azaltır. FPGA'nın yeniden programlanabilirliği " +
  "ile loader'ın güncellenebilirliği birleştiğinde döngüsel ekonomiye katkı sağlanır; " +
  "SKA 12 (Sorumlu Üretim ve Tüketim) ile uyumludur (PÇ8)."));

// ================= 5. PROJE YONETIMI =================
body.push(H1("5. PROJE YÖNETİMİ VE TAKIM ÇALIŞMASI"));
body.push(H2("5.1. Görev Dağılımı ve Sorumluluk Matrisi"));
body.push(P([R("Aşağıdaki RACI matrisi takım içi iş bölümünü göstermektedir " +
  "(R=Sorumlu, A=Onaylayan, C=Danışılan, I=Bilgilendirilen). Üye adları ve harfler " +
  "takımca doldurulacaktır (PÇ12, PÇ13): ", {}), PH("[üyeleri yazın]")]));
body.push(TABLE([3360, 2000, 2000, 2000], [
  ["İş paketi", "Üye 1", "Üye 2", "Üye 3"],
  ["Assembler genişletme (XOR/XORI/LBU)", PH_cell(), PH_cell(), PH_cell()],
  ["Host yazılımı + CRC + paket", PH_cell(), PH_cell(), PH_cell()],
  ["UART/SoC (Verilog)", PH_cell(), PH_cell(), PH_cell()],
  ["Loader (RV32I) + ISS doğrulama", PH_cell(), PH_cell(), PH_cell()],
  ["Test programları + board demo", PH_cell(), PH_cell(), PH_cell()],
  ["Rapor + sunum", PH_cell(), PH_cell(), PH_cell()],
]));
body.push(CAP("Tablo 5.1. RACI sorumluluk matrisi (takımca doldurulacak)."));
body.push(P("Projenin fazlı zaman çizelgesi Şekil 5.1'de verilmiştir; donanım fazları " +
  "(UART/SoC ve loader) öne alınarak entegrasyon riski erken yönetilmiştir (PÇ13)."));
body.push(...IMG("fig_gantt.png", 600, 257, "Şekil 5.1. Proje 3 fazlı zaman çizelgesi (Gantt)."));
body.push(H2("5.2. Koordinasyon ve Sürüm Kontrol Yönetimi"));
body.push(P("Proje, git sürüm kontrol sistemi ile yönetilmiştir. Geliştirme bir özellik " +
  "(feature) dalında yapılıp her doğrulanmış aşama sonunda ana dala (main) aktarılmıştır; " +
  "böylece ana dal her zaman çalışır durumda tutulmuştur. Her commit, ilgili fazın " +
  "doğrulama sonuçlarıyla (regresyon testleri geçmeden ilerlenmemiştir) birlikte " +
  "kaydedilmiştir. Aşamalar: (0) araç zinciri genişletme, (2) host + CRC, (1) UART SoC, " +
  "(3/4) loader + ISS doğrulama, (5) test programları + buton donanımı (PÇ13)."));
body.push(P([R("Üretken yapay zekâ beyanı: ", { bold: true }),
  R("Projenin geliştirilmesi ve raporun taslaklanması sürecinde üretken yapay zekâ " +
  "araçlarından yararlanılmıştır; tüm tasarım kararları, kodlar ve sonuçlar takım " +
  "tarafından gözden geçirilip doğrulanmıştır.")]));

// ================= 6. BIREYSEL =================
body.push(H1("6. BİREYSEL KATKI BEYANI"));
body.push(P("Bu bölüm her öğrenci tarafından ayrı ayrı doldurulacak ve imzalanacaktır. " +
  "\"Grup çalışmasından bağımsız olarak hangi spesifik modülleri tek başıma tasarladım? " +
  "Bu süreçte karşılaştığım ve tek başıma çözdüğüm en büyük teknik problem neydi?\""));
for (let i = 1; i <= 3; i++) {
  body.push(H3(`Öğrenci ${i}`));
  body.push(P([PH("[Ad Soyad — Öğrenci No]")], { after: 60 }));
  body.push(P([PH("[Bağımsız tasarladığım modül(ler) ve çözdüğüm en büyük teknik problem — " +
    "detaylıca yazın.]")], { after: 60 }));
  body.push(P([R("İmza: ", {}), PH("________________")], { after: 160 }));
}

// ================= 7. KAYNAKCA =================
body.push(H1("7. KAYNAKÇA"));
const refs = [
  "[1] A. Waterman ve K. Asanović (ed.), \"The RISC-V Instruction Set Manual, Volume I: " +
    "Unprivileged ISA\", RISC-V International, 2019.",
  "[2] C. Wolf, \"PicoRV32 — A Size-Optimized RISC-V CPU,\" YosysHQ, GitHub deposu (ISC " +
    "Lisansı). [Çevrimiçi]. https://github.com/YosysHQ/picorv32",
  "[3] P. Koopman ve T. Chakravarty, \"Cyclic Redundancy Code (CRC) Polynomial Selection " +
    "for Embedded Networks,\" Int. Conf. on Dependable Systems and Networks (DSN), " +
    "IEEE/IFIP, 2004, ss. 145–154.",
  "[4] L. L. Beck, \"System Software: An Introduction to Systems Programming,\" 3. baskı, " +
    "Addison-Wesley, 1997 (Bootstrap Loader, Bölüm 3).",
  "[5] ITU-T Recommendation V.41, \"Code-independent error-control system,\" Uluslararası " +
    "Telekomünikasyon Birliği (CRC-CCITT, polinom 0x1021).",
  "[6] Sipeed, \"Tang Nano 9K Documentation,\" Sipeed Wiki. [Çevrimiçi]. " +
    "https://wiki.sipeed.com/hardware/en/tang/Tang-Nano-9K/Nano-9K.html",
  "[7] D. A. Patterson ve J. L. Hennessy, \"Computer Organization and Design: The " +
    "RISC-V Edition,\" Morgan Kaufmann, 2017.",
];
refs.forEach(r => body.push(P([R(r, { size: SZ_SMALL })], { after: 80 })));

// helper that needs to exist before use (hoisted via function decl)
function PH_cell() { return [new TextRun({ text: "[…]", font: FONT, size: SZ_SMALL,
  highlight: "yellow", bold: true })]; }

// ================= DOCUMENT =================
const doc = new Document({
  creator: "BIL302 Proje 3",
  styles: {
    default: { document: { run: { font: FONT, size: SZ } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 26, bold: true, color: ACCENT },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 22, bold: true, color: ACCENT },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 20, bold: true },
        paragraph: { spacing: { before: 140, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 260 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [ new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [ R("BIL302 — Proje 3  |  Sayfa ", { size: SZ_SMALL }),
        new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: SZ_SMALL }) ] }) ] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(process.argv[2] || "BIL302_PROJE3.docx", buf);
  console.log("OK written", (process.argv[2] || "BIL302_PROJE3.docx"));
});
