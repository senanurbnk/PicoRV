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


# ---------------- Sekil 2.1 — Sistem mimarisi ----------------
def fig_arch():
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")

    # Panel cerceveleri
    ax.add_patch(Rectangle((0.1, 0.2), 3.6, 4.6, fill=False, ls="--", ec="#999999"))
    ax.add_patch(Rectangle((5.0, 0.2), 4.9, 4.6, fill=False, ls="--", ec="#999999"))
    ax.text(1.9, 4.65, "PC (host)", ha="center", fontsize=11, fontweight="bold", color=ACCENT)
    ax.text(7.45, 4.65, "Tang Nano 9K (GW1NR-9)", ha="center", fontsize=11,
            fontweight="bold", color=ACCENT)

    # Sol kolon (toolchain)
    box(ax, 0.5, 3.9, 2.8, 0.55, "uygulama.s", FILL2)
    box(ax, 0.5, 3.05, 2.8, 0.55, "assembler + linker", FILL2)
    box(ax, 0.5, 2.2, 2.8, 0.55, "uygulama.bin / .hex", FILL2)
    box(ax, 0.5, 1.05, 2.8, 0.75, "host_loader.py\n(paket + CRC16)", FILL, bold=True)
    arrow(ax, 1.9, 3.9, 1.9, 3.62)
    arrow(ax, 1.9, 3.05, 1.9, 2.77)
    arrow(ax, 1.9, 2.2, 1.9, 1.82)

    # Sag taraf (SoC)
    box(ax, 6.7, 3.9, 2.7, 0.55, "PicoRV32 (RV32I)", FILL, bold=True)
    box(ax, 6.7, 3.05, 2.7, 0.5, "Bus / Adres Çözücü", FILL2)
    box(ax, 5.25, 1.05, 1.9, 1.2, "BRAM 16KB\nloader@0x0\napp@0x3000", GREEN)
    box(ax, 7.25, 1.05, 1.05, 1.2, "GPIO\nLED+\nbuton", ORANGE)
    box(ax, 8.4, 1.05, 1.0, 1.2, "UART\n0x2000\n_0000", ORANGE)
    arrow(ax, 8.05, 3.9, 8.05, 3.57, style="<|-|>")
    arrow(ax, 6.2, 3.05, 6.2, 2.27, style="<|-|>")   # bus-bram
    arrow(ax, 7.75, 3.05, 7.75, 2.27, style="<|-|>") # bus-gpio
    arrow(ax, 8.9, 3.05, 8.9, 2.27, style="<|-|>")   # bus-uart

    # Orta: UART baglantisi — kutularin ALTINDAki temiz seritte (y=0.55)
    arrow(ax, 2.0, 1.05, 2.0, 0.55, style="-")            # host_loader'dan asagi stub
    arrow(ax, 8.9, 0.55, 8.9, 1.05)                        # UART'a yukari (okbasli)
    arrow(ax, 2.0, 0.55, 8.9, 0.55, style="<|-|>")         # iki yonlu veri seridi
    ax.text(5.45, 0.66, "USB-UART   AA55|CMD|LEN|ADDR|DATA|CRC16   /   ACK·NAK",
            ha="center", va="bottom", fontsize=8, color=ACCENT)

    fig.tight_layout()
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


# ---------------- Sekil 2.3 — Loader FSM ----------------
def fig_fsm():
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    ax.set_xlim(0, 9.2); ax.set_ylim(0, 5.2); ax.axis("off")
    box(ax, 0.4, 3.9, 1.9, 0.8, "IDLE / SYNC\n(0xAA 0x55)", FILL, bold=True)
    box(ax, 3.4, 3.9, 2.1, 0.8, "HEADER\nCMD,LEN,ADDR", FILL2)
    box(ax, 6.6, 3.9, 2.2, 0.8, "DATA\nLEN bayt -> RAM", GREEN)
    box(ax, 6.6, 2.2, 2.2, 0.8, "CRC\nkarşılaştır", FILL2)
    box(ax, 3.4, 2.2, 2.1, 0.8, "ACK (0x06)\nNAK (0x15)", ORANGE)
    box(ax, 3.4, 0.5, 2.1, 0.8, "JUMP 0x3000\n(JALR)", FILL, bold=True)

    arrow(ax, 2.3, 4.3, 3.4, 4.3, text="AA55")
    arrow(ax, 5.5, 4.3, 6.6, 4.3, text="oku")
    arrow(ax, 7.7, 3.9, 7.7, 3.0, text="her bayt CRC")
    arrow(ax, 6.6, 2.6, 5.5, 2.6, text="eşit değil -> NAK")
    arrow(ax, 4.45, 2.2, 2.0, 2.2, style="-|>", rad=0.0)
    arrow(ax, 1.3, 2.2, 1.3, 3.9, text="döngü")
    # START -> JUMP
    arrow(ax, 7.7, 2.2, 7.7, 0.9, color=ACCENT)
    arrow(ax, 6.6, 0.9, 5.5, 0.9, text="CMD=START")
    ax.text(7.85, 1.55, "eşit &\nSTART", fontsize=8, color=ACCENT, va="center")
    fig.tight_layout()
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
