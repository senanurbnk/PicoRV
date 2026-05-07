// =============================================================
// bram.v — Synchronous Block RAM with hardcoded init + $readmemh
// =============================================================
// 32-bit word-addressed BRAM. Per-byte write-strobe destekler
// (wstrb[i] = 1 ise i'inci byte yazilir).
//
// INIT STRATEJISI (iki katmanli):
//   1) Hardcoded inline init: blink.hex icerigi initial bloga
//      gomulu. Gowin GowinSynthesis $readmemh'yi sessizce yok
//      sayarsa ya da blink.hex bulunamazsa bile BRAM dolu basliyor.
//   2) $readmemh override: dosya bulunabilirse uzerine yazar.
//
// Yazilim degisikligi durumunda:
//   - blink.hex'i firmware/blink/build/'den buraya kopyala
//   - Asagidaki INLINE INIT bloguna yeni icerigi yapistir (bu
//     blok firmware/blink/build/blink.hex ile birebir uyusmali)
//
// Tang Nano 9K (Gowin GW1NR-9): 26 x 18Kbit BSRAM; 8KB icin 4 yeterli.
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
        // NOT: for-loop ile 2048 hucreyi sifirlamak Gowin synth loop
        // limitini (2000) asar. Gerek de yok: Gowin GowinSynthesis
        // inferred BSRAM'da explicit init edilmemis hucreleri 0'a
        // default'lar. Bu yuzden sadece program kodunu yazmak yeterli.

        // ----- INLINE INIT (firmware/blink/build/blink.hex ile birebir) -----
        mem[ 0] = 32'h100002b7;  // 0x00: LUI   t0, 0x10000   (GPIO base)
        mem[ 1] = 32'h00000313;  // 0x04: ADDI  t1, x0, 0     (sayac)
        mem[ 2] = 32'h0062a023;  // 0x08: SW    t1, 0(t0)     (LED'lere yaz)
        mem[ 3] = 32'h00130313;  // 0x0C: ADDI  t1, t1, 1
        mem[ 4] = 32'h008000ef;  // 0x10: JAL   ra, +8        (CALL delay_loop)
        mem[ 5] = 32'hff5ff06f;  // 0x14: JAL   x0, -12       (J loop)
        mem[ 6] = 32'h001003b7;  // 0x18: LUI   t2, 0x100     (delay_loop)
        mem[ 7] = 32'hfff38393;  // 0x1C: ADDI  t2, t2, -1    (spin)
        mem[ 8] = 32'hfe039ee3;  // 0x20: BNE   t2, x0, -4
        mem[ 9] = 32'h00008067;  // 0x24: JALR  x0, x1, 0     (RET)
        // -------------------------------------------------------------------

        // Override: dosya bulunabilirse uzerine yaz. Gowin sessizce
        // ignore ederse hardcoded degerler kalir; sorun olmaz.
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
