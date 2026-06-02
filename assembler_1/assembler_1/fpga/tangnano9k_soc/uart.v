// =============================================================
// uart.v — Minimal 8N1 UART (TX + RX) MMIO peripheral
// =============================================================
// Tang Nano 9K on-board USB-UART (BL702 köprüsü):
//   uart_tx = FPGA pin 17 (FPGA çıkışı → PC RX)
//   uart_rx = FPGA pin 18 (FPGA girişi ← PC TX)
//   IO_TYPE = LVCMOS33, Bank 2 (MSPI ile çakışmaz)
//
// MMIO register (SoC tarafında 0x2000_0000 bloğuna decode edilir):
//   reg_addr (=mem_addr[3:2])
//     0 (+0x00) UART_DATA   : yaz=TX byte; oku=RX byte[7:0] (okuma rx_valid'i temizler)
//     1 (+0x04) UART_STATUS : bit0=rx_valid, bit1=tx_busy
//
// Yazilim sözlesmesi (loader buna uyar):
//   - TX: önce STATUS.tx_busy=0 bekle, sonra DATA'ya yaz. (Bus stall YOK;
//         busy iken yapilan yazma yok sayilir.)
//   - RX: STATUS.rx_valid=1 olunca DATA oku (okuma rx_valid'i düsürür).
//
// wr_en / rd_en: SoC tek-cycle erisim strobe'lari (mem_valid && mem_ready).
//
// 8N1: 1 start (0) + 8 data (LSB first) + 1 stop (1). Parity yok.
// DIV = CLK_FREQ / BAUD. 27 MHz @ 9600 -> 2812 ; @ 115200 -> 234.
// =============================================================

module uart #(
    parameter integer CLK_FREQ = 27_000_000,
    parameter integer BAUD     = 9600
) (
    input  wire        clk,
    input  wire        resetn,
    // MMIO bus (SoC tarafindan decode edilmis)
    input  wire        wr_en,       // 1-cycle: DATA/STATUS'a yazma transaction'i
    input  wire        rd_en,       // 1-cycle: okuma transaction'i
    input  wire [1:0]  reg_addr,    // mem_addr[3:2]
    input  wire [31:0] wdata,
    output reg  [31:0] rdata,
    // Seri hat
    input  wire        rx,
    output wire        tx
);
    localparam integer DIV  = (CLK_FREQ / BAUD);
    localparam integer DIV2 = (CLK_FREQ / BAUD) / 2;

    localparam [1:0] REG_DATA   = 2'd0;
    localparam [1:0] REG_STATUS = 2'd1;

    // -------------------------------------------------------------
    // TX: 8N1, LSB-first, shift register
    // -------------------------------------------------------------
    reg        tx_active;
    reg [9:0]  tx_shift;     // {stop=1, data[7:0], start=0}, tx_shift[0] hatta
    reg [3:0]  tx_bitcnt;    // 10..1
    reg [15:0] tx_div;

    assign tx = tx_active ? tx_shift[0] : 1'b1;   // idle = 1
    wire tx_busy = tx_active;

    wire wr_data = wr_en && (reg_addr == REG_DATA);

    always @(posedge clk) begin
        if (!resetn) begin
            tx_active <= 1'b0;
            tx_div    <= 16'd0;
            tx_bitcnt <= 4'd0;
            tx_shift  <= 10'h3FF;
        end else if (!tx_active) begin
            if (wr_data) begin
                tx_shift  <= {1'b1, wdata[7:0], 1'b0};  // stop, data, start
                tx_bitcnt <= 4'd10;
                tx_div    <= DIV[15:0] - 16'd1;
                tx_active <= 1'b1;
            end
        end else if (tx_div != 16'd0) begin
            tx_div <= tx_div - 16'd1;
        end else begin
            tx_div   <= DIV[15:0] - 16'd1;
            tx_shift <= {1'b1, tx_shift[9:1]};          // sag kaydir, idle=1 doldur
            tx_bitcnt <= tx_bitcnt - 4'd1;
            if (tx_bitcnt == 4'd1)
                tx_active <= 1'b0;
        end
    end

    // -------------------------------------------------------------
    // RX: 8N1, orta-bit örnekleme, 2-FF senkronizer
    // -------------------------------------------------------------
    reg rx_q, rx_qq;
    always @(posedge clk) begin
        rx_q  <= rx;
        rx_qq <= rx_q;
    end

    reg        rx_active;
    reg [15:0] rx_div;
    reg [3:0]  rx_bitcnt;    // 0=start-merkez, 1..8=data, 9=stop
    reg [7:0]  rx_shift;
    reg [7:0]  rx_data;
    reg        rx_valid;

    wire rd_data = rd_en && (reg_addr == REG_DATA);

    always @(posedge clk) begin
        if (!resetn) begin
            rx_active <= 1'b0;
            rx_valid  <= 1'b0;
            rx_div    <= 16'd0;
            rx_bitcnt <= 4'd0;
        end else begin
            // Okuma rx_valid'i temizler (asagidaki stop-set daha sonra geldigi
            // icin ayni cycle'da yeni byte gelirse valid korunur).
            if (rd_data)
                rx_valid <= 1'b0;

            if (!rx_active) begin
                if (!rx_qq) begin                   // start biti (hat low)
                    rx_active <= 1'b1;
                    rx_div    <= DIV2[15:0] - 16'd1; // yarim bit -> start merkezi
                    rx_bitcnt <= 4'd0;
                end
            end else if (rx_div != 16'd0) begin
                rx_div <= rx_div - 16'd1;
            end else begin
                rx_div <= DIV[15:0] - 16'd1;
                if (rx_bitcnt == 4'd0) begin
                    rx_bitcnt <= 4'd1;              // start merkezi geçildi
                end else if (rx_bitcnt <= 4'd8) begin
                    rx_shift  <= {rx_qq, rx_shift[7:1]};   // LSB-first
                    rx_bitcnt <= rx_bitcnt + 4'd1;
                end else begin
                    // stop biti merkezi: byte tamam
                    rx_data   <= rx_shift;
                    rx_valid  <= 1'b1;
                    rx_active <= 1'b0;
                end
            end
        end
    end

    // -------------------------------------------------------------
    // Okuma mux (kombinasyonel; SoC 1-cycle ready ile örnekler)
    // -------------------------------------------------------------
    always @(*) begin
        case (reg_addr)
            REG_DATA:   rdata = {24'b0, rx_data};
            REG_STATUS: rdata = {30'b0, tx_busy, rx_valid};
            default:    rdata = 32'b0;
        endcase
    end
endmodule
