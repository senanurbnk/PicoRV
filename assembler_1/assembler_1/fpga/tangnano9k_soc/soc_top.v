// =============================================================
// soc_top.v — Tang Nano 9K + PicoRV32 minimal SoC
// =============================================================
//
// Bellek haritasi:
//   0x00000000 - 0x00001FFF   .text    (BRAM 8 KB, $readmemh init)
//   0x10000000                 GPIO     (alt 6 bit -> LED'ler)
//
// Bus: PicoRV32'nin native MEM_VALID/MEM_READY interface'i.
// Adres decode: mem_addr[31:28]
//   4'h0  -> BRAM
//   4'h1  -> GPIO
//   diger -> ready=1, rdata=0 (no-op; CPU takilmasin)
//
// Reset: btn_reset_n active-low (Tang Nano 9K BTN1).
// Power-on'da 16 cycle reset asserted; sonra normal calisma.
//
// Clock: 27 MHz Tang Nano 9K kristal osilatoru.
// =============================================================

module soc_top (
    input  wire        clk_27mhz,
    input  wire        btn_reset_n,    // active-low
    output wire [5:0]  led_n           // active-low LEDs (Tang Nano 9K)
);
    // -------------------------------------------------------------
    // Reset synchronizer + power-on counter
    // -------------------------------------------------------------
    reg [3:0]  reset_cnt = 4'b0;
    reg        resetn    = 1'b0;
    always @(posedge clk_27mhz) begin
        if (!btn_reset_n) begin
            reset_cnt <= 4'b0;
            resetn    <= 1'b0;
        end else if (reset_cnt != 4'hF) begin
            reset_cnt <= reset_cnt + 1'b1;
            resetn    <= 1'b0;
        end else begin
            resetn    <= 1'b1;
        end
    end

    // -------------------------------------------------------------
    // PicoRV32 native bus (slave-side)
    // -------------------------------------------------------------
    wire        mem_valid;
    wire        mem_instr;
    wire        mem_ready;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [3:0]  mem_wstrb;
    wire [31:0] mem_rdata;

    // -------------------------------------------------------------
    // Adres decode
    // -------------------------------------------------------------
    wire bram_sel = (mem_addr[31:28] == 4'h0);
    wire gpio_sel = (mem_addr[31:28] == 4'h1);
    wire other_sel = ~(bram_sel | gpio_sel);

    // -------------------------------------------------------------
    // BRAM (8 KB, sync)
    // -------------------------------------------------------------
    wire [31:0] bram_rdata;
    bram #(
        .ADDR_BITS(11),
        .INIT_FILE("blink.hex")
    ) u_bram (
        .clk(clk_27mhz),
        .wstrb(bram_sel ? mem_wstrb : 4'b0),
        .waddr(mem_addr[12:2]),
        .raddr(mem_addr[12:2]),
        .wdata(mem_wdata),
        .rdata(bram_rdata)
    );

    // -------------------------------------------------------------
    // GPIO (LED MMIO)
    // -------------------------------------------------------------
    wire [31:0] gpio_rdata;
    wire [5:0]  led_value;
    gpio #(.LED_COUNT(6)) u_gpio (
        .clk(clk_27mhz),
        .sel(gpio_sel),
        .wstrb(mem_wstrb),
        .wdata(mem_wdata),
        .led_value(led_value),
        .rdata(gpio_rdata)
    );

    // Tang Nano 9K LED'leri active-low: yazilim "1=ON" gorur,
    // donanimda burada terslenir.
    assign led_n = ~led_value;

    // -------------------------------------------------------------
    // Read mux + 1-cycle ready strobe
    // -------------------------------------------------------------
    // BRAM senkron oldugu icin ready'yi 1 cycle gecikmeli ureti riz.
    // GPIO ve "other" da 1-cycle strobe kullanir (basit/uniform).
    reg ready_d;
    always @(posedge clk_27mhz) begin
        if (!resetn)
            ready_d <= 1'b0;
        else
            ready_d <= mem_valid && !ready_d;
    end
    assign mem_ready = ready_d;

    assign mem_rdata = bram_sel ? bram_rdata
                     : gpio_sel ? gpio_rdata
                     : 32'h0000_0000;

    // -------------------------------------------------------------
    // PicoRV32 CPU instance
    // -------------------------------------------------------------
    picorv32 #(
        .ENABLE_COUNTERS(0),
        .ENABLE_COUNTERS64(0),
        .ENABLE_REGS_16_31(1),
        .ENABLE_REGS_DUALPORT(1),
        .LATCHED_MEM_RDATA(0),
        .TWO_STAGE_SHIFT(1),
        .BARREL_SHIFTER(0),
        .TWO_CYCLE_COMPARE(0),
        .TWO_CYCLE_ALU(0),
        .COMPRESSED_ISA(0),
        .CATCH_MISALIGN(0),
        .CATCH_ILLINSN(0),
        .ENABLE_PCPI(0),
        .ENABLE_MUL(0),
        .ENABLE_FAST_MUL(0),
        .ENABLE_DIV(0),
        .ENABLE_IRQ(0),
        .ENABLE_IRQ_QREGS(0),
        .ENABLE_IRQ_TIMER(0),
        .ENABLE_TRACE(0),
        .REGS_INIT_ZERO(0),
        .MASKED_IRQ(32'h0000_0000),
        .LATCHED_IRQ(32'hFFFF_FFFF),
        .PROGADDR_RESET(32'h0000_0000),
        .PROGADDR_IRQ(32'h0000_0010),
        .STACKADDR(32'h0000_2000)
    ) u_cpu (
        .clk      (clk_27mhz),
        .resetn   (resetn),
        .trap     (),
        .mem_valid(mem_valid),
        .mem_instr(mem_instr),
        .mem_ready(mem_ready),
        .mem_addr (mem_addr),
        .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb),
        .mem_rdata(mem_rdata),
        .mem_la_read (),
        .mem_la_write(),
        .mem_la_addr (),
        .mem_la_wdata(),
        .mem_la_wstrb(),
        .pcpi_valid(),
        .pcpi_insn (),
        .pcpi_rs1  (),
        .pcpi_rs2  (),
        .pcpi_wr   (1'b0),
        .pcpi_rd   (32'h0),
        .pcpi_wait (1'b0),
        .pcpi_ready(1'b0),
        .irq       (32'h0),
        .eoi       (),
        .trace_valid(),
        .trace_data ()
    );
endmodule
