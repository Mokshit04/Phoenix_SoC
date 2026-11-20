#!/usr/bin/env python3
"""Draws the Phoenix SoC architecture block diagram as an SVG."""
import sys

W, H = 1800, 1250
INK, MUTED, BG = "#18212D", "#566273", "#FFFFFF"

# function colours: (fill, stroke)
CPU = ("#E8F0FC", "#2A62C9")
CLU = ("#F5F8FE", "#2A62C9")
BUS = ("#27313F", "#27313F")
MEM = ("#E3F4F1", "#16806F")
PER = ("#FDF3DF", "#B0750F")
ACC = ("#F1EAFB", "#6B3FB8")
REC = ("#FCEAE8", "#C23B2E")
SYS = ("#EEF1F5", "#566273")

out = []
def add(s): out.append(s)

def box(x, y, w, h, col, dashed=False, r=10, sw=2.2):
    dash = ' stroke-dasharray="9 6"' if dashed else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{col[0]}" '
        f'stroke="{col[1]}" stroke-width="{sw}"{dash}/>')

def text(x, y, s, size=16, weight=400, fill=INK, anchor="middle", italic=False):
    st = ' font-style="italic"' if italic else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}"{st}>{s}</text>')

def block(x, y, w, h, col, title, lines, dashed=False, tsize=20, lsize=15, top=None, r=10):
    box(x, y, w, h, col, dashed, r)
    cx = x + w / 2
    n = len(lines)
    total = tsize + n * (lsize + 7)
    ty = (y + (h - total) / 2 + tsize) if top is None else y + top
    text(cx, ty, title, tsize, 700, col[1] if col is not BUS else "#FFFFFF")
    for i, ln in enumerate(lines):
        text(cx, ty + (i + 1) * (lsize + 7) + 2, ln, lsize, 400,
             INK if col is not BUS else "#D9E0EA")

def arrow(x1, y1, x2, y2, col=INK, both=False, dashed=False, sw=2.4):
    dash = ' stroke-dasharray="7 5"' if dashed else ""
    ms = ' marker-start="url(#as)"' if both else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{sw}"'
        f'{dash} marker-end="url(#ae)"{ms}/>')

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
    f'font-family="Inter, DejaVu Sans, Arial, sans-serif">')
add('<defs>'
    '<marker id="ae" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
    '<path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker>'
    '<marker id="as" viewBox="0 0 10 10" refX="1.5" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
    '<path d="M10,0 L0,5 L10,10 z" fill="context-stroke"/></marker>'
    '</defs>')
add(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

# ---------------------------------------------------------------- title
text(50, 62, "Phoenix SoC — system architecture", 36, 700, INK, "start")
text(50, 96, "Architecture frozen, 19 November 2026.  Logic verified in a cycle-level model; "
             "no block has RTL yet.", 17, 400, MUTED, "start")

# ---------------------------------------------------------------- clock / reset
block(50, 150, 240, 170, SYS, "Clock and reset",
      ["One clock for the whole SoC", "Reset: active low,", "async assert, sync release"],
      tsize=19, lsize=14.5)
arrow(8, 205, 48, 205, MUTED)
text(5, 193, "CLK", 12, 600, MUTED, "start")
arrow(8, 265, 48, 265, MUTED)
text(5, 253, "RST_N", 12, 600, MUTED, "start")
arrow(292, 235, 338, 235, MUTED)

# ---------------------------------------------------------------- deferred list
box(50, 360, 240, 460, ("#FAFBFC", "#9AA4B2"), dashed=True, sw=1.6)
text(170, 392, "Deferred", 19, 700, MUTED)
text(170, 414, "(deliberately not drawn)", 13.5, 400, MUTED)
for i, ln in enumerate(["eFPGA fabric", "Partial reconfiguration", "(FPGA only)",
                        "Two-core degraded mode",
                        "Debug module / JTAG", "Boot ROM and loader", "DMA, SPI, I²C",
                        "Interrupt controller", "Fabrication"]):
    ind = ln.startswith("(")
    text(170, 452 + i * 32 - (8 if ind else 0), ln, 13.5 if ind else 15, 400, MUTED)

# ---------------------------------------------------------------- CPU cluster
box(340, 150, 800, 350, CLU, sw=2.4, r=14)
text(360, 181, "PHX_CORE — redundant CPU cluster", 21, 700, CPU[1], "start")
text(1120, 181, "three cores in lockstep", 15, 400, MUTED, "end")
for i, (nm, dashed) in enumerate([("A", False), ("B", True), ("C", True)]):
    x = 370 + i * 255
    block(x, 200, 230, 140, CPU, f"Ibex core {nm}",
          ["RV32IMC, 2-stage", "instruction port + data port"], dashed=dashed, lsize=14.5)
    arrow(x + 115, 342, x + 115, 378, CPU[1])
block(370, 380, 740, 100, REC, "Voting stage",
      ["Majority voters: 103 output bits, bitwise 2-of-3",
       "Discrepancy detector: names the core that disagrees"], dashed=True, lsize=15)

# ---------------------------------------------------------------- recovery manager
block(1300, 150, 450, 350, REC, "PHX_RM — recovery manager",
      ["Detect → save state → reset cores",
       "→ restore state → verify", "",
       "If recovery keeps failing:",
       "retry, then system reset, then safe state", "",
       "Periodic scrub · watchdog timer",
       "Bus-timeout faults: reset or isolate one target",
       "Fault injection and latency counters"],
      dashed=True, lsize=14.5, top=42)
# links cluster <-> RM
text(1220, 222, "resync interrupt", 14, 600, REC[1])
arrow(1298, 232, 1144, 232, REC[1], dashed=True)
text(1220, 292, "core reset", 14, 600, REC[1])
arrow(1298, 302, 1144, 302, REC[1], dashed=True)
text(1220, 420, "mismatch flags", 14, 600, REC[1])
arrow(1112, 430, 1296, 430, REC[1], dashed=True)
# fault pin
arrow(1690, 148, 1690, 112, REC[1], dashed=True)
text(1678, 126, "FAULT pin", 14, 600, REC[1], "end")

# ---------------------------------------------------------------- buses
arrow(480, 482, 480, 556, INK, both=True)
text(492, 530, "voted instruction port", 14, 600, INK, "start")
arrow(800, 482, 800, 556, INK, both=True)
text(812, 530, "voted data port", 14, 600, INK, "start")

block(340, 560, 280, 64, BUS, "PHX_BUS v1.0 · I-channel", ["fetch only, point to point"],
      tsize=17, lsize=13.5, r=8)
box(660, 560, 1090, 64, BUS, r=8)
text(1205, 587, "PHX_BUS v1.0 · D-channel", 18, 700, "#FFFFFF")
text(1205, 610, "address decoder  ·  response mux  ·  error response for unmapped addresses  ·  "
                "timeout monitor", 13.5, 400, "#D9E0EA")
# RM registers on the D-channel
arrow(1525, 502, 1525, 556, REC[1], both=True, dashed=True)
text(1537, 534, "status and control registers", 14, 600, REC[1], "start")

# ---------------------------------------------------------------- targets
block(340, 690, 280, 130, MEM, "IMEM", ["Instruction memory", "synchronous RAM"])
arrow(480, 626, 480, 686, INK, both=True)

tx = [660 + i * 185 for i in range(6)]
tg = [
    (MEM, "DMEM", ["Data memory", "SECDED (39,32) ECC"], False),
    (PER, "GPIO", ["16 pins", "ADR-006"], False),
    (PER, "Timer", ["32-bit", "ADR-007"], False),
    (PER, "PWM", ["2 channels", "ADR-008"], False),
    (PER, "UART", ["8N1, TX + RX", "new"], False),
    (ACC, "PHX_ACC", ["Accelerator slot", "set by profiling"], True),
]
for x, (col, t, ls, d) in zip(tx, tg):
    block(x, 690, 165, 130, col, t, ls, dashed=d, lsize=14.5)
    arrow(x + 82.5, 626, x + 82.5, 686, INK, both=True, dashed=d)

# ---------------------------------------------------------------- pins
add(f'<line x1="640" y1="872" x2="1750" y2="872" stroke="#9AA4B2" stroke-width="1.6" '
    f'stroke-dasharray="3 6"/>')
text(1750, 864, "chip boundary", 13, 400, MUTED, "end")
for x, lab in [(tx[1], "GPIO[15:0]"), (tx[3], "PWM[1:0]"), (tx[4], "TX / RX")]:
    arrow(x + 82.5, 822, x + 82.5, 906, PER[1], both=(lab != "PWM[1:0]"))
    text(x + 82.5, 930, lab, 14.5, 600, PER[1])

# ---------------------------------------------------------------- legend
ly = 985
text(50, ly, "How to read it", 17, 700, INK, "start")
items = [(CPU, "Processor"), (BUS, "Interconnect"), (MEM, "Memory"), (PER, "Peripherals"),
         (ACC, "Accelerator"), (REC, "Recovery logic")]
x = 50
for col, lab in items:
    add(f'<rect x="{x}" y="{ly + 18}" width="26" height="18" rx="4" fill="{col[0]}" '
        f'stroke="{col[1]}" stroke-width="2"/>')
    text(x + 36, ly + 33, lab, 15, 400, INK, "start")
    x += 58 + len(lab) * 9.2
add(f'<rect x="50" y="{ly + 56}" width="46" height="20" rx="4" fill="none" stroke="{INK}" stroke-width="2.2"/>')
text(108, ly + 72, "Solid outline: built first, as a single-core SoC", 15, 400, INK, "start")
add(f'<rect x="520" y="{ly + 56}" width="46" height="20" rx="4" fill="none" stroke="{INK}" '
    f'stroke-width="2.2" stroke-dasharray="9 6"/>')
text(578, ly + 72, "Dashed outline: added once that works (cores B and C, voting, PHX_RM, accelerator)",
     15, 400, INK, "start")

# ---------------------------------------------------------------- notes
ny = 1118
add(f'<line x1="50" y1="{ny - 26}" x2="1750" y2="{ny - 26}" stroke="#D5DBE3" stroke-width="1.4"/>')
notes = [
    "Only what the cores send out is voted. Read data, grants, responses and interrupts are wired "
    "identically to all three cores, so they stay in step.",
    "Interrupts go straight to Ibex inputs: Timer on the timer line; UART, PHX_ACC and PHX_RM on "
    "fast-interrupt lines. No interrupt controller is needed.",
    "Voters, discrepancy detector and PHX_RM are single copies. A fault inside them is not masked; "
    "this is an accepted, documented limitation.",
    "Address regions: IMEM 0x0000_0000 · DMEM 0x2000_0000 · peripherals 0x4000_0000 · "
    "accelerators 0x5000_0000 · PHX_RM 0xE000_0000.",
]
for i, n in enumerate(notes):
    text(50, ny + i * 27, n, 14.5, 400, MUTED, "start")

add("</svg>")
open(sys.argv[1], "w").write("\n".join(out))
