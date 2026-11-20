#!/usr/bin/env python3
"""Phoenix SoC - formal top-level block diagram (for faculty review)."""
import sys

W, H = 2000, 1500
INK, MUTED, RULE = "#111827", "#4B5563", "#9CA3AF"
CPU = ("#EEF3FB", "#1F4E9E")
REC = ("#FBEFEE", "#A8322A")
MEM = ("#EAF5F2", "#17705F")
PER = ("#FBF4E4", "#8A5A0B")
ACC = ("#F2EDFA", "#5B35A0")
SYS = ("#F1F3F6", "#374151")
BUS = ("#1F2937", "#1F2937")
WHITE = ("#FFFFFF", "#374151")

o = []
def add(s): o.append(s)

def rect(x, y, w, h, col, dashed=False, r=4, sw=1.8):
    d = ' stroke-dasharray="8 5"' if dashed else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{col[0]}" stroke="{col[1]}" stroke-width="{sw}"{d}/>')

def t(x, y, s, size=14, weight=400, fill=INK, anchor="middle", mono=False):
    fam = ' font-family="DejaVu Sans Mono, monospace"' if mono else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{fam}>{s}</text>')

def block(x, y, w, h, col, title, lines, dashed=False, ts=17, ls=13, lead=18, top=None, tcol=None):
    rect(x, y, w, h, col, dashed)
    cx = x + w / 2
    total = ts + len(lines) * lead
    ty = y + (h - total) / 2 + ts if top is None else y + top
    t(cx, ty, title, ts, 700, tcol or col[1])
    for i, ln in enumerate(lines):
        t(cx, ty + (i + 1) * lead + 1, ln, ls)

def arrow(x1, y1, x2, y2, col=INK, both=False, dashed=False, sw=1.8):
    d = ' stroke-dasharray="6 4"' if dashed else ""
    ms = ' marker-start="url(#as)"' if both else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{sw}"{d} marker-end="url(#ae)"{ms}/>')

def line(x1, y1, x2, y2, col=INK, sw=1.8, dashed=False):
    d = ' stroke-dasharray="6 4"' if dashed else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{sw}"{d}/>')

def table(x, y, title, widths, rows, rh=25):
    t(x, y - 9, title, 15, 700, INK, "start")
    tw = sum(widths)
    for i, row in enumerate(rows):
        yy = y + i * rh
        fill = "#E5E9F0" if i == 0 else "#FFFFFF"
        add(f'<rect x="{x}" y="{yy}" width="{tw}" height="{rh}" fill="{fill}" stroke="{RULE}" stroke-width="1"/>')
        cx = x
        for j, (wd, cell) in enumerate(zip(widths, row)):
            if j:
                line(cx, yy, cx, yy + rh, RULE, 1)
            t(cx + 8, yy + 17, cell, 12.5, 700 if i == 0 else 400, INK, "start")
            cx += wd

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Inter, DejaVu Sans, Arial, sans-serif">')
add('<defs><marker id="ae" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker>'
    '<marker id="as" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10,0 L0,5 L10,10 z" fill="context-stroke"/></marker></defs>')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')
add(f'<rect x="14" y="14" width="{W-28}" height="{H-28}" fill="none" stroke="{INK}" stroke-width="1.5"/>')

# ---- header
t(40, 62, "Phoenix SoC: Top-Level Architecture Block Diagram", 30, 700, INK, "start")
t(40, 92, "A modular 32-bit RISC-V system-on-chip with a self-recovery-oriented architecture", 16, 400, MUTED, "start")
t(W - 40, 56, "Department of ECE, PDEU Gandhinagar", 14, 600, INK, "end")
t(W - 40, 77, "Harit Patel, Mokshit Lattha  |  Mentor: Dr. Gunjan Thakur", 13.5, 400, MUTED, "end")
t(W - 40, 97, "19 November 2026  |  Status: architecture frozen, verified in a pre-RTL model; RTL not yet written", 13.5, 400, MUTED, "end")
line(40, 112, W - 40, 112, INK, 1.2)

# ---- clock and reset
rect(84, 150, 256, 410, SYS)
t(212, 180, "CLOCK AND RESET", 16, 700, SYS[1])
block(98, 198, 228, 58, WHITE, "Clock distribution", ["single system clock"], ts=14, ls=12.5, lead=17)
block(98, 268, 228, 92, WHITE, "Reset synchronisers", ["active-low reset,", "asynchronous assert,", "synchronous release"], ts=14, ls=12.5, lead=17)
t(98, 388, "Reset outputs", 13.5, 700, INK, "start")
for i, s_ in enumerate(["Power-on: entire SoC", "System: all but fault history",
                        "Core: CPU cluster only", "Target: one peripheral"]):
    t(98, 410 + i * 21, "•  " + s_, 12.5, 400, INK, "start")
t(98, 506, "Every asynchronous input is", 12, 400, MUTED, "start")
t(98, 523, "synchronised once, then fanned", 12, 400, MUTED, "start")
t(98, 540, "out to all three cores.", 12, 400, MUTED, "start")
arrow(26, 228, 82, 228); t(26, 218, "CLK", 12, 700, INK, "start")
arrow(26, 315, 82, 315); t(26, 305, "RST_N", 12, 700, INK, "start")
arrow(342, 228, 398, 228); t(370, 220, "clock", 12, 400, MUTED)
arrow(342, 315, 398, 315); t(370, 307, "resets", 12, 400, MUTED)

# ---- CPU cluster
rect(400, 150, 860, 410, CPU, sw=2.2)
t(420, 180, "PHX_CORE: REDUNDANT CPU CLUSTER", 16, 700, CPU[1], "start")
t(1240, 180, "triple modular redundancy, cores in lockstep", 13, 400, MUTED, "end")
for i, (nm, d) in enumerate([("A", False), ("B", True), ("C", True)]):
    x = 425 + i * 275
    block(x, 198, 250, 112, WHITE, f"Ibex core {nm}",
          ["RV32IMC, 2-stage pipeline", "3-cycle multiplier", "instruction port, data port"],
          dashed=d, ts=15.5, ls=12.5, lead=17, tcol=CPU[1])
    line(x + 125, 310, x + 125, 338, CPU[1])
line(425, 338, 1225, 338, CPU[1], 2.4)
t(1225, 330, "bus outputs of A, B, C (103 bits per core)", 12, 400, MUTED, "end")
vb = [(425, "Majority voter: instruction port", ["instr_req, instr_addr[31:0]", "33 bits, bitwise 2-of-3"]),
      (700, "Majority voter: data port", ["data_req, data_we, data_be[3:0],", "data_addr[31:0], data_wdata[31:0]", "70 bits, bitwise 2-of-3"]),
      (975, "Discrepancy detector", ["compares A, B, C every cycle", "flags the core that disagrees,", "or that no majority exists"])]
for x, ttl, ls in vb:
    arrow(x + 125, 338, x + 125, 362, CPU[1])
    block(x, 364, 250, 112, REC, ttl, ls, dashed=True, ts=14, ls=12.5, lead=17)
t(850, 500, "Voter output per bit:  Y = A·B + B·C + A·C", 13, 700, INK, "start")
t(850, 519, "Inputs to the cores (read data, grant, valid, error,", 12, 400, MUTED, "start")
t(850, 535, "interrupts, reset) are not voted. They are distributed", 12, 400, MUTED, "start")
t(850, 551, "identically to all three cores.", 12, 400, MUTED, "start")

# ---- recovery manager
rect(1410, 150, 550, 410, REC, dashed=True, sw=2.2)
t(1430, 180, "PHX_RM: RECOVERY MANAGER", 16, 700, REC[1], "start")
block(1430, 198, 510, 96, WHITE, "Recovery state machine",
      ["monitor → detect → classify → isolate → save state →",
       "reset all cores → restore state → verify (N cycles)",
       "on failure: retry (M times) → system reset → safe state"], ts=14.5, ls=12.5, lead=17, tcol=REC[1])
sub = [(1430, 308, "Fault history register", ["survives system reset;", "cleared by power-on reset"]),
       (1692, 308, "Timers and counters", ["scrub, watchdog, and cycle", "time stamps for latency"]),
       (1430, 396, "Target control", ["per-peripheral reset", "and isolate bits"]),
       (1692, 396, "Fault injection (test)", ["reset one core, or invert", "one core's output bits"])]
for x, y, ttl, ls in sub:
    block(x, y, 248, 76, WHITE, ttl, ls, ts=13.5, ls=12, lead=16, tcol=REC[1])
t(1685, 500, "Outputs: resynchronisation interrupt, core reset, target reset,", 12.5, 400, MUTED)
t(1685, 517, "system-reset request, safe-state signal, FAULT pin", 12.5, 400, MUTED)
t(1685, 541, "Registers are memory-mapped at 0xE000_0000", 12.5, 600, INK)
arrow(1880, 148, 1880, 122, REC[1]); t(1868, 136, "FAULT", 12, 700, REC[1], "end")
# cluster <-> RM
t(1335, 222, "resynchronisation", 12, 600, REC[1]); t(1335, 237, "interrupt (fast IRQ 0)", 12, 600, REC[1])
arrow(1408, 246, 1264, 246, REC[1], dashed=True)
t(1335, 290, "core reset", 12, 600, REC[1])
arrow(1408, 299, 1264, 299, REC[1], dashed=True)
t(1335, 405, "mismatch flags", 12, 600, REC[1]); t(1335, 437, "(one per core)", 12, 400, REC[1])
arrow(1227, 414, 1406, 414, REC[1], dashed=True)

# ---- ports to buses
arrow(550, 478, 550, 636, INK, both=True)
t(562, 588, "↓ request, address", 12.5, 400, INK, "start")
t(562, 606, "↑ grant, valid, read data, error", 12.5, 400, INK, "start")
t(562, 624, "voted instruction port", 12.5, 700, INK, "start")
arrow(825, 478, 825, 636, INK, both=True)
t(837, 588, "↓ request, address, write enable, byte enables, write data", 12.5, 400, INK, "start")
t(837, 606, "↑ grant, valid, read data, error", 12.5, 400, INK, "start")
t(837, 624, "voted data port", 12.5, 700, INK, "start")

# ---- buses
rect(400, 640, 320, 84, BUS)
t(560, 668, "PHX_BUS v1.0: I-CHANNEL", 15, 700, "#FFFFFF")
t(560, 690, "instruction fetch, read-only", 12.5, 400, "#D1D5DB")
t(560, 708, "point to point, 32-bit", 12.5, 400, "#D1D5DB")
rect(760, 640, 1200, 84, BUS)
t(1360, 664, "PHX_BUS v1.0: D-CHANNEL  (32-bit address, 32-bit data, request / grant / response-valid handshake)", 14.5, 700, "#FFFFFF")
chips = ["Address decoder (address[31:28])", "Response multiplexer", "Default target: error response", "Timeout monitor"]
cw = [300, 220, 290, 200]; cx = 760 + (1200 - sum(cw) - 3 * 16) / 2
for s, w_ in zip(chips, cw):
    add(f'<rect x="{cx}" y="{678}" width="{w_}" height="32" rx="3" fill="#374151" stroke="#6B7280" stroke-width="1"/>')
    t(cx + w_ / 2, 699, s, 12.5, 400, "#F3F4F6")
    cx += w_ + 16
# RM <-> D-channel
arrow(1500, 562, 1500, 636, REC[1], both=True, dashed=True); t(1510, 606, "register access", 12, 600, REC[1], "start")
arrow(1690, 636, 1690, 562, REC[1], dashed=True); t(1700, 606, "timeout flags", 12, 600, REC[1], "start")
arrow(1850, 562, 1850, 636, REC[1], dashed=True); t(1840, 606, "isolate", 12, 600, REC[1], "end")

# ---- targets
block(400, 800, 320, 180, MEM, "IMEM",
      ["Instruction memory", "base 0x0000_0000", "synchronous single-port RAM", "vector table and program code",
       "first instruction at 0x0000_0080"], ts=17, ls=12.5, lead=18)
arrow(560, 726, 560, 796, INK, both=True)
tg = [(MEM, "DMEM", ["Data memory", "base 0x2000_0000", "SECDED (39,32) ECC,", "byte enables", "data, stack, saved state"], False, None),
      (PER, "GPIO", ["16 pins, bidirectional", "region 0x4000_0000", "ODR, IDR, DIR,", "SET, CLEAR, TOGGLE", "2-flop input synchroniser"], False, None),
      (PER, "TIMER", ["32-bit up counter", "region 0x4000_0000", "prescaler, compare,", "control, status", "one-shot / auto-reload"], False, "IRQ"),
      (PER, "PWM", ["2 channels", "region 0x4000_0000", "16-bit counter, prescaler,", "period, 2 duty registers", "comparator-based"], False, None),
      (PER, "UART", ["8N1, transmit + receive", "region 0x4000_0000", "programmable baud", "divider", "event reporting, console"], False, "IRQ"),
      (ACC, "PHX_ACC", ["Accelerator slot", "base 0x5000_0000", "control, status, data", "registers", "function set by profiling"], True, "IRQ")]
xs = [760 + i * 203 for i in range(6)]
for x, (col, ttl, ls, d, irq) in zip(xs, tg):
    block(x, 800, 185, 180, col, ttl, ls, dashed=d, ts=17, ls=12.5, lead=18)
    arrow(x + 92.5, 726, x + 92.5, 796, INK, both=True, dashed=d)
    if irq:
        add(f'<rect x="{x+185-48}" y="{806}" width="42" height="20" rx="3" fill="#FFFFFF" stroke="{col[1]}" stroke-width="1.2"/>')
        t(x + 185 - 27, 821, "IRQ", 11.5, 700, col[1])

# ---- pins
line(740, 1030, 1960, 1030, RULE, 1.4, dashed=True)
t(1960, 1022, "chip boundary", 12, 400, MUTED, "end")
for x, lab, both in [(xs[1], "GPIO[15:0]", True), (xs[3], "PWM[1:0]", False), (xs[4], "UART_TX, UART_RX", True)]:
    arrow(x + 92.5, 982, x + 92.5, 1056, PER[1], both=both)
    t(x + 92.5, 1076, lab, 13, 700, PER[1])

# ---- legend (left, beside buses)
rect(84, 640, 256, 340, ("#FFFFFF", RULE), sw=1.2)
t(100, 668, "LEGEND", 14, 700, INK, "start")
for i, (col, lab) in enumerate([(CPU, "Processor"), (BUS, "Interconnect"), (MEM, "Memory"), (PER, "Peripheral"),
                                (ACC, "Accelerator"), (REC, "Recovery logic")]):
    add(f'<rect x="100" y="{684 + i*27}" width="26" height="16" rx="2" fill="{col[0]}" stroke="{col[1]}" stroke-width="1.5"/>')
    t(138, 697 + i * 27, lab, 12.5, 400, INK, "start")
add(f'<rect x="100" y="854" width="26" height="16" rx="2" fill="none" stroke="{INK}" stroke-width="1.6"/>')
t(138, 867, "Single-core baseline", 12.5, 400, INK, "start")
add(f'<rect x="100" y="881" width="26" height="16" rx="2" fill="none" stroke="{INK}" stroke-width="1.6" stroke-dasharray="6 4"/>')
t(138, 894, "Added after baseline", 12.5, 400, INK, "start")
add(f'<rect x="100" y="908" width="34" height="16" rx="3" fill="#FFFFFF" stroke="{INK}" stroke-width="1.2"/>'); t(117, 920, "IRQ", 10.5, 700, INK)
t(146, 921, "Has interrupt output", 12.5, 400, INK, "start")
arrow(102, 948, 132, 948, INK, both=True); t(144, 953, "Request and response", 12.5, 400, INK, "start")

# ---- tables
ty = 1150
table(40, ty, "Address map", [150, 130, 300],
      [["Region", "Base address", "Contents"], ["Code", "0x0000_0000", "IMEM"], ["Data", "0x2000_0000", "DMEM"],
       ["Peripherals", "0x4000_0000", "GPIO, Timer, PWM, UART"], ["Accelerators", "0x5000_0000", "PHX_ACC"],
       ["System", "0xE000_0000", "PHX_RM registers"], ["All other", "reserved", "error response"]])
table(680, ty, "Interrupt connections (no interrupt controller)", [290, 300],
      [["Source", "Ibex input"], ["PHX_RM resynchronisation request", "fast interrupt 0 (highest priority)"],
       ["Timer", "timer interrupt"], ["UART", "fast interrupt line"], ["PHX_ACC done", "fast interrupt line"],
       ["NMI, software, external inputs", "tied off"]])
table(1330, ty, "Fault classes handled", [60, 270, 300],
      [["", "Fault", "Response"], ["F1", "Transient upset in one core's state", "voter masks it; PHX_RM resynchronises"],
       ["F2", "Peripheral stops responding", "timeout, error response, reset or isolate"],
       ["F3", "Bit flip in a data-memory word", "SECDED corrects 1 bit, flags 2"],
       ["F4", "Hidden fault / program hang", "periodic scrub / watchdog"],
       ["", "Recovery fails repeatedly", "system reset, then safe state + FAULT"],
       ["", "Not covered", "IMEM contents, voter, bus, PHX_RM itself"]])

line(40, 1372, W - 40, 1372, RULE, 1)
notes = ["Recovery sequence: a mismatch is detected and located; the two healthy cores save the processor state to DMEM through the voters; all three cores are reset together;"
         " the state is restored and the program resumes; PHX_RM then checks N cycles for agreement.",
         "The CPU cluster presents one instruction port and one data port to the rest of the SoC, so the bus, memories and peripherals are identical for the one-core and three-core builds.",
         "Implementation: one shared RTL for two tracks, an FPGA prototype and RTL-to-GDSII in the SAED 32 nm educational library. Fabrication is not planned in this phase.",
         "Not part of this architecture: embedded FPGA fabric, dynamic partial reconfiguration, ECC on IMEM, debug module, boot loader, DMA, SPI, I²C."]
for i, n in enumerate(notes):
    t(40, 1396 + i * 22, n, 12.5, 400, MUTED, "start")
add("</svg>")
open(sys.argv[1], "w").write("\n".join(o))
