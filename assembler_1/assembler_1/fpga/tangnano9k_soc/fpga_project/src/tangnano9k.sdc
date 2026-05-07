// =============================================================
// tangnano9k.sdc — Timing constraints (Gowin)
// =============================================================
// 27 MHz tek clock domain'i. Bu kadar dusuk frekansta picorv32 +
// 8KB BRAM rahatca timing kapatir; sadece tool'a clock periyodunu
// soylemek yeterli.
// =============================================================

create_clock -name clk_27mhz -period 37.037 -waveform {0 18.5} [get_ports {clk_27mhz}]
