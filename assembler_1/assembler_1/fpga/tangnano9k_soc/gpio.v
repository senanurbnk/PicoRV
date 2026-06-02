// =============================================================
// gpio.v — Memory-mapped LED çıkışı + buton girişi
// =============================================================
// MMIO (soc_top.v decode: 0x1000_0000):
//   +0x00 (reg_addr=0)  LED   : Yaz=wdata[5:0]->led_value ; Oku=led_value
//   +0x04 (reg_addr=1)  BTN   : Oku=btn_in (bit0, 1=basili) ; Yaz=yok
//
// Tang Nano 9K LED'leri ACTIVE-LOW (cikis 0 -> LED on). Inversion soc_top.v'de.
// Butonlar da ACTIVE-LOW; soc_top.v ham pini tersleyip btn_in'e "1=basili" verir.
// =============================================================

module gpio #(
    parameter LED_COUNT = 6,
    parameter BTN_COUNT = 1
) (
    input  wire                  clk,
    input  wire                  sel,           // adres decode'undan
    input  wire [3:0]            wstrb,
    input  wire [1:0]            reg_addr,      // mem_addr[3:2]: 0=LED, 1=BTN
    input  wire [31:0]           wdata,
    input  wire [BTN_COUNT-1:0]  btn_in,        // soft-side: 1=basili
    output reg  [LED_COUNT-1:0]  led_value,     // soft-side: 1=ON
    output reg  [31:0]           rdata
);
    initial led_value = {LED_COUNT{1'b0}};

    // Yazma: yalniz +0 (LED)
    always @(posedge clk) begin
        if (sel && |wstrb && reg_addr == 2'd0)
            led_value <= wdata[LED_COUNT-1:0];
    end

    // Okuma mux (kombinasyonel)
    always @(*) begin
        case (reg_addr)
            2'd0:    rdata = {{(32-LED_COUNT){1'b0}}, led_value};   // LED
            2'd1:    rdata = {{(32-BTN_COUNT){1'b0}}, btn_in};      // BUTON
            default: rdata = 32'b0;
        endcase
    end
endmodule
