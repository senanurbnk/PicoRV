# -*- coding: utf-8 -*-
"""Rapor sekilleri (PNG) ureticisi: mimari, paket cercevesi, loader FSM, Gantt."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

plt.rcParams["font.family"] = "monospace"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
os.makedirs(OUT, exist_ok=True)

ACCENT = "#1F3864"
FILL   = "#D9E2F3"
FILL2  = "#E8EEF7"
WHITE  = "#FFFFFF"
GREEN  = "#E2EFDA"
ORANGE = "#FCE4D6"


def box(ax, x, y, w, h, text, fill=WHITE, fs=10, bold=False, edge=ACCENT):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                       linewidth=1.4, edgecolor=edge, facecolor=fill)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal", color="#1A1A1A")


def arrow(ax, x1, y1, x2, y2, text=None, fs=8, color=ACCENT, style="-|>", rad=0.0):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
                        linewidth=1.3, color=color,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, text, ha="center", va="bottom",
                fontsize=fs, color=color)


# ---------------- Sekil 2.1 — Sistem mimarisi (detayli) ----------------
def fig_arch():
    fig, ax = plt.subplots(figsize=(13.2, 8.0))
    ax.set_xlim(0, 13.2); ax.set_ylim(0, 8.0); ax.axis("off")
    fs = 8.5

    # --- Konteynerler ---
    ax.add_patch(Rectangle((0.15, 0.35), 3.55, 7.2, fill=False, ls="--", ec="#888888"))
    ax.text(1.92, 7.62, "PC (Host) — Toolchain", ha="center", fontsize=11.5,
            fontweight="bold", color=ACCENT)
    ax.add_patch(Rectangle((5.55, 0.35), 7.5, 7.2, fill=False, ls="--", ec="#888888"))
    ax.text(9.3, 7.62, "Tang Nano 9K (GW1NR-9) — soc_top.v", ha="center", fontsize=11.5,
            fontweight="bold", color=ACCENT)

    # --- HOST zinciri ---
    xb, wb = 0.4, 3.05
    box(ax, xb, 6.75, wb, 0.55, "uygulama.s / .asm\n(RV32I kaynak)", FILL2, fs)
    box(ax, xb, 5.75, wb, 0.8,
        "Assembler (two-pass)\nparser·opcode_table·encoder\nsymbol_table·bit_layout", FILL, fs)
    box(ax, xb + 0.25, 5.05, wb - 0.5, 0.45, ".o.json (PICORV-OBJ)", "#FFF2CC", fs)
    box(ax, xb, 4.05, wb, 0.8,
        "Linker (two-pass)\nlinker.py·linker_script\nPass1 layout / Pass2 reloc", FILL, fs)
    box(ax, xb + 0.25, 3.35, wb - 0.5, 0.45, "hex_emitter (.bin/.hex/_init.vh)", "#FFF2CC", fs)
    box(ax, xb, 2.25, wb, 0.85,
        "host_loader.py\npacket.py + crc.py (CRC-16)\nblok·ACK/NAK·retry", FILL, fs, bold=True)
    box(ax, xb + 0.25, 1.55, wb - 0.5, 0.45, "uygulama.bin (host girdisi)", "#FFF2CC", fs)
    cx = xb + wb / 2
    for y1, y2 in [(6.75, 6.55), (5.75, 5.5), (5.05, 4.85), (4.05, 3.8),
                   (3.35, 3.1), (2.25, 2.0)]:
        arrow(ax, cx, y1, cx, y2, style="-|>")

    # --- Orta: seri hat ---
    box(ax, 4.0, 5.7, 1.4, 0.95, "USB-C\nseri hat\n9600→115200", "#E1D5E7", fs)
    ax.text(4.7, 4.95, "Paket:", ha="center", fontsize=fs, color=ACCENT, fontweight="bold")
    ax.text(4.7, 4.62, "SYNC|CMD|LEN|\nADDR|DATA|CRC16", ha="center", fontsize=7.6,
            color=ACCENT)

    # --- FPGA SoC ---
    box(ax, 5.85, 6.75, 3.0, 0.55, "BL702 USB-UART köprüsü", ORANGE, fs)
    box(ax, 5.85, 5.7, 3.0, 0.8, "uart.v — 8N1\nMMIO 0x2000_0000\n+0 DATA  +4 STATUS", ORANGE, fs)
    box(ax, 9.5, 5.7, 3.3, 0.8, "PicoRV32 (RV32I)\nPROGADDR_RESET=0x0\nSTACKADDR=0x2000",
        FILL, fs, bold=True)
    box(ax, 5.95, 4.55, 6.75, 0.75,
        "Adres Çözücü (Bus) — mem_addr[31:28]:  0→BRAM  1→GPIO  2→UART\n"
        "native bus: mem_valid / mem_ready / mem_wstrb", FILL2, fs)
    box(ax, 5.85, 2.95, 3.4, 1.15,
        "BRAM 16 KB (bram.v)\nloader @0x0000–0x0FFF\nuygulama @0x3000–0x3FFF\ninit: mem_init.vh",
        GREEN, fs)
    box(ax, 9.5, 3.3, 3.3, 0.8, "gpio.v\nMMIO 0x1000_0000\n+0 LED  +4 buton", ORANGE, fs)
    box(ax, 9.5, 2.25, 3.3, 0.6, "6× LED (active-low)\npin 10,11,13,14,15,16", "#E1D5E7", fs)
    box(ax, 9.5, 1.4, 1.55, 0.55, "buton S1\npin 3", "#E1D5E7", fs)
    box(ax, 11.25, 1.4, 1.55, 0.55, "reset S2\npin 4", "#E1D5E7", fs)
    box(ax, 5.85, 2.3, 3.4, 0.45, "27 MHz osilatör — pin 52", "#F8CECC", fs)

    arrow(ax, 7.35, 6.75, 7.35, 6.5, style="<|-|>")          # bl702-uart
    ax.text(7.55, 6.62, "rx18/tx17", fontsize=7.2, color=ACCENT, va="center")
    arrow(ax, 7.35, 5.7, 7.35, 5.3, style="<|-|>")           # uart-dec
    ax.text(7.55, 5.5, "0x2000", fontsize=7.2, color=ACCENT, va="center")
    arrow(ax, 11.15, 5.7, 11.15, 5.3, style="<|-|>")         # cpu-dec
    ax.text(11.35, 5.5, "bus", fontsize=7.2, color=ACCENT, va="center")
    arrow(ax, 7.55, 4.55, 7.55, 4.1, style="<|-|>")          # dec-bram
    ax.text(7.75, 4.32, "0x0000", fontsize=7.2, color=ACCENT, va="center")
    arrow(ax, 11.15, 4.55, 11.15, 4.1, style="<|-|>")        # dec-gpio
    ax.text(11.35, 4.32, "0x1000", fontsize=7.2, color=ACCENT, va="center")
    arrow(ax, 10.3, 3.3, 10.3, 2.85, style="-|>")            # gpio-leds
    # btn-gpio: sag gutter'dan, LED kutusunu kesmeden
    arrow(ax, 11.05, 1.67, 12.95, 1.67, style="-")
    arrow(ax, 12.95, 1.67, 12.95, 3.70, style="-")
    arrow(ax, 12.95, 3.70, 12.8, 3.70, style="-|>")
    ax.text(12.9, 2.05, "buton girişi", fontsize=7.0, color=ACCENT, ha="right", va="center")
    ax.text(7.55, 2.88, "clk →", fontsize=7.2, color="#B85450", va="center")  # saat kaynagi (örtük)

    # --- Host <-> FPGA seri kopru: sol gutter'dan yukari, kutulara dokunmaz ---
    SER = "#6c8ebf"
    arrow(ax, cx, 2.25, cx, 0.70, style="-", color=SER)        # host_loader -> alt serit
    arrow(ax, cx, 0.70, 5.70, 0.70, style="-", color=SER)      # yatay alt serit
    arrow(ax, 5.70, 0.70, 5.70, 7.02, style="-", color=SER)    # FPGA sol gutter'da yukari
    arrow(ax, 5.70, 7.02, 5.85, 7.02, style="-|>", color=SER)  # BL702'ye gir
    ax.text((cx + 5.70) / 2, 0.80,
            "seri hat:  veri paketleri (+CRC16)   /   ACK 0x06 · NAK 0x15",
            fontsize=8, color=SER, ha="center", va="bottom")

    fig.savefig(os.path.join(OUT, "fig_arch.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------- Sekil 2.2 — Paket cercevesi ----------------
def fig_packet():
    fig, ax = plt.subplots(figsize=(10, 2.3))
    ax.set_xlim(0, 10); ax.set_ylim(0, 2.3); ax.axis("off")
    fields = [("SYNC\n0xAA 0x55", "2B", FILL),
              ("CMD", "1B", FILL2),
              ("LEN", "1B", FILL2),
              ("ADDR\n(LE)", "4B", FILL2),
              ("DATA", "LEN bayt", GREEN),
              ("CRC16\n(LE)", "2B", ORANGE)]
    widths = [1.7, 1.0, 1.0, 1.6, 2.7, 1.5]
    x = 0.25
    for (name, size, fill), w in zip(fields, widths):
        box(ax, x, 1.05, w, 0.85, name, fill, fs=9.5, bold=True)
        ax.text(x + w / 2, 0.82, size, ha="center", va="top", fontsize=8.5, color="#555555")
        x += w + 0.02
    ax.text(5.0, 0.35, "CRC-16/CCITT-FALSE  (poly 0x1021, init 0xFFFF, MSB-first) — "
            "SYNC hariç CMD..DATA üzerinden",
            ha="center", fontsize=8.5, color=ACCENT)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_packet.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------- Sekil 2.3 — Loader FSM (detayli akis) ----------------
def _dia(ax, cx, cy, w, h, text, fs=8.3):
    from matplotlib.patches import Polygon
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    ax.add_patch(Polygon(pts, closed=True, facecolor="#FFF2CC", edgecolor="#D6B656",
                         linewidth=1.4))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color="#1A1A1A")


def _ell(ax, cx, cy, w, h, text, fs=9):
    from matplotlib.patches import Ellipse
    ax.add_patch(Ellipse((cx, cy), w, h, facecolor=GREEN, edgecolor="#82B366",
                         linewidth=1.4))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, fontweight="bold")


def _bc(ax, cx, cy, w, h, text, fill=FILL, fs=8.3, bold=False):  # center-anchored box
    box(ax, cx - w / 2, cy - h / 2, w, h, text, fill, fs, bold)


def fig_fsm():
    fig, ax = plt.subplots(figsize=(9.5, 11.0))
    ax.set_xlim(0, 10); ax.set_ylim(0, 12); ax.axis("off")
    X = 4.5
    _ell(ax, X, 11.5, 2.0, 0.55, "RESET\nPC=0x0000", 8.5)
    _bc(ax, X, 10.7, 3.6, 0.5, "IDLE — getc() ile bayt bekle")
    _dia(ax, X, 9.65, 2.0, 0.95, "byte == 0xAA ?")
    _dia(ax, X, 8.45, 2.0, 0.95, "byte == 0x55 ?")
    _bc(ax, X, 7.6, 3.6, 0.45, "crc = 0xFFFF")
    _bc(ax, X, 6.65, 4.0, 0.85,
        "HEADER\nCMD=getc; LEN=getc; ADDR[0..3]=getc×4\n(her bayt crc16_byte)", FILL2)
    _bc(ax, X, 5.75, 3.6, 0.45, "i = 0 ;  ptr = ADDR")
    _dia(ax, X, 4.75, 2.0, 0.95, "i < LEN ?")
    _bc(ax, 7.85, 4.75, 2.7, 1.0,
        "DATA\nb = getc()\nSB b → [ptr]\ncrc16_byte; i++; ptr++", GREEN)
    _bc(ax, X, 3.9, 3.8, 0.45, "rx_crc = getc | (getc<<8)")
    _dia(ax, X, 2.85, 2.2, 1.0, "crc == rx_crc ?")
    _bc(ax, 1.4, 2.95, 2.3, 0.5, "putc NAK (0x15)", "#F8CECC")
    _dia(ax, X, 1.5, 2.2, 1.0, "CMD == START ?")
    _bc(ax, 1.4, 1.6, 2.3, 0.5, "putc ACK (0x06)", GREEN)
    _bc(ax, X, 0.5, 3.8, 0.5, "JUMP — JALR x0,0(s4) → 0x3000", FILL, 8.3, True)
    _ell(ax, 8.2, 0.5, 2.6, 0.7, "uygulama\nçalışır", 8.5)

    # Leaf not kutusu
    box(ax, 6.2, 7.55, 3.6, 2.7,
        "Leaf altprogramlar (stack yok):\n"
        " getc : rx_valid bekle, LW DATA\n"
        " putc : tx_busy bekle, SW DATA\n"
        " crc16_byte : CRC-16/CCITT\n"
        "   (host crc.py ile birebir)\n\n"
        "Kalıcı reg: s0=UART s1=crc\n"
        " s2=cmd s3=len s4=addr\n"
        " s5=rx_crc s6=i s7=ptr",
        "#F5F5F5", 7.6)

    A = dict(style="-|>")
    arrow(ax, X, 11.22, X, 10.95, **A)
    arrow(ax, X, 10.45, X, 10.13, **A)
    arrow(ax, X, 9.18, X, 8.93, text="evet", **A)
    arrow(ax, X, 7.98, X, 7.83, text="evet", **A)
    arrow(ax, X, 7.38, X, 7.08, **A)
    arrow(ax, X, 6.22, X, 5.98, **A)
    arrow(ax, X, 5.53, X, 5.23, **A)
    arrow(ax, X + 1.0, 4.75, 6.5, 4.75, text="evet", **A)            # ddata->datastep
    arrow(ax, 6.5, 4.3, X + 0.55, 4.4, text="döngü", style="-|>", rad=0.2)  # datastep->ddata
    arrow(ax, X, 4.27, X, 4.13, text="hayır", **A)
    arrow(ax, X, 3.67, X, 3.36, **A)
    arrow(ax, X - 1.1, 2.85, 2.55, 2.95, text="hayır", **A)          # dcrc->nak
    arrow(ax, X, 2.35, X, 2.0, text="evet", **A)
    arrow(ax, X - 1.1, 1.5, 2.55, 1.6, text="hayır (WRITE/PING)", **A)  # dstart->ack
    arrow(ax, X, 1.0, X, 0.76, text="evet", **A)
    arrow(ax, X + 1.9, 0.5, 6.9, 0.5, **A)                           # jump->end
    # hayir -> IDLE donusleri (sol/sag raylar)
    arrow(ax, X - 1.0, 9.65, 2.7, 9.65, style="-", color="#999999")
    arrow(ax, 2.7, 9.65, 2.7, 10.68, style="-|>", color="#999999", text="hayır")
    arrow(ax, X - 1.0, 8.45, 2.4, 8.45, style="-", color="#999999")    # d55 hayir -> sol ray
    arrow(ax, 2.4, 8.45, 2.4, 10.62, style="-|>", color="#999999", text="hayır")
    # NAK/ACK -> IDLE (sol rayda yukari)
    arrow(ax, 0.55, 2.95, 0.3, 2.95, style="-", color="#999999")
    arrow(ax, 0.3, 2.95, 0.3, 10.7, style="-", color="#999999")
    arrow(ax, 0.3, 10.7, 2.7, 10.7, style="-|>", color="#999999", text="sonraki paket")
    arrow(ax, 0.55, 1.6, 0.45, 1.6, style="-", color="#BBBBBB")
    arrow(ax, 0.45, 1.6, 0.45, 10.55, style="-", color="#BBBBBB")

    fig.savefig(os.path.join(OUT, "fig_fsm.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


# ---------------- Sekil 5.1 — Gantt ----------------
def fig_gantt():
    fig, ax = plt.subplots(figsize=(9.2, 4.0))
    tasks = [
        ("Faz 0: Toolchain (XOR/XORI/LBU)", 0, 1, "#4472C4"),
        ("Faz 2: Host + CRC + paket",        1, 1, "#5B9BD5"),
        ("Faz 1: UART/SoC (Verilog)",        2, 2, "#70AD47"),
        ("Faz 3/4: Loader + ISS doğrulama",  3, 2, "#ED7D31"),
        ("Faz 5: Test prog. + buton",        5, 1, "#FFC000"),
        ("Faz 6: Board demo + rapor",        6, 2, "#A5A5A5"),
    ]
    for i, (name, start, dur, color) in enumerate(tasks):
        y = len(tasks) - 1 - i
        ax.barh(y, dur, left=start, height=0.55, color=color, edgecolor="#333333")
        ax.text(start + dur / 2, y, f"{dur}g", ha="center", va="center",
                fontsize=8, color="white", fontweight="bold")
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels([t[0] for t in reversed(tasks)], fontsize=9)
    ax.set_xticks(range(0, 9))
    ax.set_xticklabels([f"G{n}" for n in range(0, 9)], fontsize=8)
    ax.set_xlabel("Proje günü (göreli)", fontsize=9)
    ax.set_xlim(0, 8)
    ax.grid(axis="x", ls=":", color="#CCCCCC")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("Proje 3 Zaman Çizelgesi (Gantt)", fontsize=11, fontweight="bold",
                 color=ACCENT)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_gantt.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_arch(); fig_packet(); fig_fsm(); fig_gantt()
    from PIL import Image
    for f in ("fig_arch", "fig_packet", "fig_fsm", "fig_gantt"):
        im = Image.open(os.path.join(OUT, f + ".png"))
        print(f"{f}.png  {im.size[0]}x{im.size[1]}")
