// =============================================================
// bram.v — Synchronous Block RAM (init from $readmemh)
// =============================================================
// 32-bit word-addressed BRAM. Per-byte write-strobe destekler
// (wstrb[i] = 1 ise i'inci byte yazilir). Init dosyasi Verilog
// $readmemh formatinda olmali — bizim hex_emitter.write_verilog_hex
// fonksiyonumuzun urettigi format buna uyar.
//
// Tang Nano 9K (Gowin GW1NR-9): 26 x 18Kbit Block RAM
//   8 KB icin 4 BSRAM yetiyor. Senkron okuma (1-cycle latency)
//   Gowin'in BSRAM'ina dogal infer edilir.
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
        // Path is relative to Gowin proje kok klasoru; Gowin'de
        // INIT_FILE'i tam yolla geçirmek istersen project ayarlarinda
        // SourcePath duzenle.
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
