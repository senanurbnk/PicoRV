// =============================================================
// bram.v — Synchronous Block RAM with toolchain-driven init
// =============================================================
// 32-bit word-addressed BRAM. Per-byte write-strobe destekler.
//
// INIT KAYNAGI: blink_init.vh
//   Bu dosya `run_link.py` tarafindan otomatik uretilir
//   (firmware/blink/build/blink_init.vh) ve bram.v'nin yaninda
//   bulunmalidir. Icinde mem[i] = N'h... satirlari vardir.
//
//   `$readmemh` Gowin GowinSynthesis tarafindan sessizce ignore
//   edildigi icin onun yerine bu dosyayi `include` ediyoruz —
//   sentez asamasinda BRAM init bitstream'a baglanir.
//
// YAZILIM DEGISTIGINDE:
//   1) python run_link.py ... -o firmware/blink/build/blink
//      -> blink.hex + blink_init.vh (yeni) uretilir
//   2) blink_init.vh'yi Gowin proje src/ klasorune kopyala
//   3) Gowin: Run All
//   bram.v'ye dokunmaya gerek yok.
//
// Tang Nano 9K (Gowin GW1NR-9): inferred BSRAM. Specifiye
// edilmemis hucreler 0'a default'lanir (= ADDI x0,x0,0 = NOP).
// =============================================================

module bram #(
    parameter ADDR_BITS = 11,                  // 2K word = 8 KB
    parameter [255:0] INIT_FILE = "blink.hex"
) (
    input  wire                  clk,
    input  wire [3:0]            wstrb,        // byte-enable
    input  wire [ADDR_BITS-1:0]  waddr,        // word address (write)
    input  wire [ADDR_BITS-1:0]  raddr,        // word address (read)
    input  wire [31:0]           wdata,
    output reg  [31:0]           rdata
);
    reg [31:0] mem [0:(1<<ADDR_BITS)-1];

    initial begin
        // Toolchain'in urettigi init verisi (blink_init.vh):
        `include "blink_init.vh"

        // Yedek: bazi simulator'lar veya farkli synth tool'lari
        // $readmemh'i destekliyor olabilir. Destekliyorsa override
        // eder; etmiyorsa zarari yok.
        $readmemh(INIT_FILE, mem);
    end

    always @(posedge clk) begin
        if (wstrb[0]) mem[waddr][ 7: 0] <= wdata[ 7: 0];
        if (wstrb[1]) mem[waddr][15: 8] <= wdata[15: 8];
        if (wstrb[2]) mem[waddr][23:16] <= wdata[23:16];
        if (wstrb[3]) mem[waddr][31:24] <= wdata[31:24];
        rdata <= mem[raddr];
    end
endmodule
