# Tang Nano 9K + PicoRV32 — Linker Script
# ========================================
# .text   BRAM (8 KB) — picorv32 reset PC = 0x00000000 ile birebir.
# .data   Bu demoda kullanilmiyor (yer ayrildi, ileride aktive edilebilir).
# Entry   _start (GLOBAL olmali; zorunluluk.)

TEXT_ORIGIN = 0x00000000
TEXT_LENGTH = 0x00002000
DATA_ORIGIN = 0x00002000
DATA_LENGTH = 0x00002000
ENTRY       = _start
