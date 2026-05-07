// =============================================================
// gpio.v — Memory-mapped LED output (write-only)
// =============================================================
// MMIO adresi soc_top.v icinde decode edilir (default: 0x10000000).
// Yazma: SW gpio'ya wdata[5:0] -> led_value reg'i.
// Okuma: combinational, son yazilan degeri verir.
//
// Tang Nano 9K LED'leri ACTIVE-LOW (cikis 0 -> LED on). Soft tarafi
// "1=ON" semantikle calissin diye INVERSION soc_top.v icinde yapilir.
// =============================================================

module gpio #(
    parameter LED_COUNT = 6
) (
    input  wire                  clk,
    input  wire                  sel,           // adres decode'undan
    input  wire [3:0]            wstrb,
    input  wire [31:0]           wdata,
    output reg  [LED_COUNT-1:0]  led_value,     // soft-side: 1=ON
    output wire [31:0]           rdata
);
    initial led_value = {LED_COUNT{1'b0}};

    always @(posedge clk) begin
        if (sel && |wstrb) begin
            // Tum byte-strobe'lari kabul et (basit MMIO)
            led_value <= wdata[LED_COUNT-1:0];
        end
    end

    assign rdata = {{(32-LED_COUNT){1'b0}}, led_value};
endmodule
