#!/usr/bin/env python3
"""
Phoenix SoC - pre-RTL architecture model
========================================
A cycle-level, executable model of the Phoenix architecture. It checks the LOGIC of the
architecture before any RTL is written:

  Check 1  Voter and discrepancy detector (103 bits)
  Check 2  Address map and decoder
  Check 3  PHX_BUS D-channel: normal transfers, error response, timeout, reset, isolate
  Check 4  Fault-injection campaign on the three-core cluster with the recovery manager
  Check 5  The same faults on one unprotected core (the baseline for comparison)
  Check 6  Escalation: permanent fault, and two cores faulty at once

What it is NOT: it does not model Ibex, real timing, or gates. The "core" here is a small
register machine with the same kind of interface (fetch port, data port, interrupt, reset)
so that the voters, the bus and the recovery sequence can be exercised end to end.
Cycle counts are for this toy core only and say nothing about Ibex.

Run:  python3 phoenix_model.py            (pure Python 3, no packages needed)
      python3 phoenix_model.py --runs 5000 --seed 7
"""
import argparse, random, statistics, sys
from collections import Counter

M32 = 0xFFFFFFFF

# ----------------------------------------------------------------------------- address map
IMEM_BASE, DMEM_BASE, PERI_BASE, ACC_BASE, RM_BASE = 0x0000_0000, 0x2000_0000, 0x4000_0000, 0x5000_0000, 0xE000_0000
REGIONS = {0x0: "IMEM", 0x2: "DMEM", 0x4: "PERIPH", 0x5: "ACC", 0xE: "RM"}
GPIO_ODR = PERI_BASE + 0x0000          # example slots inside the peripheral region (model only)
UART_TX = PERI_BASE + 0x3000
RM_SP = RM_BASE                        # "saved stack pointer" register of the recovery manager
DMEM_WORDS = 1024
SAVE_AREA = DMEM_BASE + 0xF00          # where the handler saves the processor state
RESULT = DMEM_BASE + 0x800

def decode(addr):
    return REGIONS.get((addr >> 28) & 0xF)          # None -> default target (error response)

# ----------------------------------------------------------------------------- voter / detector
# bus-output vector of one core, 103 bits:
#   instr_req(1) instr_addr(32) data_req(1) data_we(1) data_be(4) data_addr(32) data_wdata(32)
def pack(ireq, iaddr, dreq, dwe, dbe, daddr, dwdata):
    v = ireq & 1
    v = (v << 32) | (iaddr & M32)
    v = (v << 1) | (dreq & 1)
    v = (v << 1) | (dwe & 1)
    v = (v << 4) | (dbe & 0xF)
    v = (v << 32) | (daddr & M32)
    v = (v << 32) | (dwdata & M32)
    return v

def unpack(v):
    dwdata = v & M32; v >>= 32
    daddr = v & M32; v >>= 32
    dbe = v & 0xF; v >>= 4
    dwe = v & 1; v >>= 1
    dreq = v & 1; v >>= 1
    iaddr = v & M32; v >>= 32
    return (v & 1, iaddr, dreq, dwe, dbe, daddr, dwdata)

VEC_BITS = 103
def vote(a, b, c):
    return (a & b) | (b & c) | (a & c)              # Y = A.B + B.C + A.C, bit by bit

def detect(vecs, voted):
    return [v != voted for v in vecs]               # one flag per core

# ----------------------------------------------------------------------------- toy program
def build_program(n_iter=60):
    """Returns (imem list, handler address). Instructions are tuples; one per word."""
    P = {}
    def put(addr, *ins):
        for i, x in enumerate(ins):
            P[addr + 4 * i] = x
    APP, RESTORE, HANDLER = 0x40, 0x100, 0x180
    # boot: resume if the recovery manager holds a saved stack pointer, else cold start
    put(0x00, ("li", 1, RM_SP), ("ld", 2, 1, 0), ("bne", 2, 0, RESTORE), ("jmp", APP))
    # application: running sums written to memory and to GPIO
    put(APP,
        ("ei",), ("li", 1, 0), ("li", 2, 0), ("li", 3, n_iter), ("li", 4, DMEM_BASE),
        ("li", 5, 0), ("li", 7, GPIO_ODR),
        # loop @ APP+28
        ("addi", 1, 1, 1), ("add", 2, 2, 1), ("st", 2, 4, 0), ("ld", 6, 4, 0), ("add", 5, 5, 6),
        ("st", 1, 7, 0), ("addi", 4, 4, 4), ("bne", 1, 3, APP + 28),
        ("li", 4, RESULT), ("st", 2, 4, 0), ("st", 5, 4, 4), ("li", 6, UART_TX), ("st", 5, 6, 0),
        ("halt",))
    # resynchronisation handler: save state through the (voted) data port, tell PHX_RM, wait
    h = [("st", r, 0, SAVE_AREA + 4 * r) for r in range(1, 8)]
    h += [("csrr", 1), ("st", 1, 0, SAVE_AREA + 32), ("li", 1, SAVE_AREA), ("st", 1, 0, RM_SP),
          ("jmp", HANDLER + 4 * 11)]
    put(HANDLER, *h)
    # restore (r2 = saved pointer from boot code)
    r = [("ld", 1, 2, 32), ("csrw", 1)] + [("ld", k, 2, 4 * k) for k in range(3, 8)]
    r += [("st", 0, 0, RM_SP), ("ld", 1, 2, 4), ("ld", 2, 2, 8), ("mret",)]
    put(RESTORE, *r)
    size = max(P) // 4 + 1
    imem = [P.get(4 * i, ("halt",)) for i in range(size)]
    return imem, HANDLER

# ----------------------------------------------------------------------------- toy core
F_REQ, F_WAIT, EX, D_WAIT, HALT, TRAP = range(6)

class Core:
    def __init__(self, handler):
        self.handler = handler
        self.stuck = None                # permanent fault: ("pc", bit) forced to 1 every cycle
        self.reset()
    def reset(self):
        self.pc, self.mepc, self.ie, self.state = 0, 0, 0, F_REQ
        self.r = [0] * 8
        self.ir = None
        self.apply_stuck()
    def apply_stuck(self):
        if self.stuck:
            self.pc |= (1 << self.stuck[1])
    def out(self, irq):
        """Combinational bus outputs for this cycle."""
        if self.state == F_REQ and not (irq and self.ie):
            return pack(1, self.pc, 0, 0, 0, 0, 0)
        if self.state == EX and self.ir[0] in ("ld", "st"):
            op = self.ir
            addr = (self.r[op[2]] + op[3]) & M32
            if op[0] == "st":
                return pack(0, 0, 1, 1, 0xF, addr, self.r[op[1]])
            return pack(0, 0, 1, 0, 0xF, addr, 0)
        return pack(0, 0, 0, 0, 0, 0, 0)
    def step(self, irq, i_resp, d_resp):
        s = self.state
        if s == F_REQ:
            if irq and self.ie:
                self.mepc, self.ie, self.pc = self.pc, 0, self.handler
            else:
                self.state = F_WAIT
        elif s == F_WAIT:
            if i_resp is not None:
                data, err = i_resp
                if err or data is None: self.state = TRAP
                else: self.ir, self.state = data, EX
        elif s == EX:
            op = self.ir; k = op[0]; nxt = (self.pc + 4) & M32
            if k in ("ld", "st"):
                self.state = D_WAIT
            else:
                if k == "li": self.r[op[1]] = op[2] & M32
                elif k == "add": self.r[op[1]] = (self.r[op[2]] + self.r[op[3]]) & M32
                elif k == "addi": self.r[op[1]] = (self.r[op[2]] + op[3]) & M32
                elif k == "bne":
                    if self.r[op[1]] != self.r[op[2]]: nxt = op[3]
                elif k == "jmp": nxt = op[1]
                elif k == "ei": self.ie = 1
                elif k == "csrr": self.r[op[1]] = self.mepc
                elif k == "csrw": self.mepc = self.r[op[1]]
                elif k == "mret": nxt, self.ie = self.mepc, 1
                elif k == "halt": self.state = HALT; nxt = self.pc
                self.r[0] = 0
                if self.state == EX:
                    self.pc, self.state = nxt, F_REQ
        elif s == D_WAIT:
            if d_resp is not None:
                data, err = d_resp
                if err: self.state = TRAP
                else:
                    if self.ir[0] == "ld": self.r[self.ir[1]] = data & M32
                    self.r[0] = 0
                    self.pc, self.state = (self.pc + 4) & M32, F_REQ
        self.apply_stuck()
    # ---- fault injection: flip one bit of processor state
    TARGETS = ["pc", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "mepc", "ie", "state"]
    def flip(self, target, bit):
        if target == "pc": self.pc ^= 1 << bit
        elif target == "mepc": self.mepc ^= 1 << bit
        elif target == "ie": self.ie ^= 1
        elif target == "state": self.state = (self.state ^ (1 << (bit % 2))) % 4
        else: self.r[int(target[1])] ^= 1 << bit
    def snapshot(self):
        return (self.pc, self.mepc, self.ie, self.state, tuple(self.r))

# ----------------------------------------------------------------------------- bus + targets
class Bus:
    """I-channel (point to point to IMEM) and D-channel (decoder, error target, timeout)."""
    def __init__(self, imem, rm=None, timeout=16):
        self.imem, self.rm, self.timeout = imem, rm, timeout
        self.dmem = [0] * DMEM_WORDS
        self.i_pending = self.d_pending = None
        self.d_wait = None                     # outstanding request to a target that is not answering
        self.trace = []                        # application-visible writes (memory + peripherals)
        self.stuck, self.isolated = set(), set()
        self.timeout_log = []
    def drop_pending(self):
        self.i_pending = self.d_pending = self.d_wait = None
    def responses(self):
        """Responses delivered this cycle (for requests granted earlier)."""
        i, d = self.i_pending, self.d_pending
        self.i_pending = self.d_pending = None
        if self.d_wait is not None:            # timeout monitor
            self.d_wait[1] += 1
            if self.d_wait[1] >= self.timeout:
                self.timeout_log.append(self.d_wait[0])
                if self.rm: self.rm.timeout_flag(self.d_wait[0])
                d, self.d_wait = (0, 1), None
        return i, d
    def request(self, voted):
        ireq, iaddr, dreq, dwe, dbe, daddr, dwdata = unpack(voted)
        if ireq:
            idx = iaddr >> 2
            ok = decode(iaddr) == "IMEM" and iaddr % 4 == 0 and idx < len(self.imem)
            self.i_pending = (self.imem[idx], 0) if ok else (None, 1)
        if dreq:
            tgt = decode(daddr)
            if tgt in self.isolated:
                self.d_pending = (0, 1)                        # isolated target: immediate error
            elif tgt in self.stuck:
                self.d_wait = [tgt, 0]                         # granted, never answered
            elif tgt == "DMEM":
                idx = (daddr - DMEM_BASE) >> 2
                if idx >= DMEM_WORDS: self.d_pending = (0, 1)
                elif dwe:
                    self.dmem[idx] = dwdata
                    if daddr < SAVE_AREA: self.trace.append((daddr, dwdata))
                    self.d_pending = (0, 0)
                else: self.d_pending = (self.dmem[idx], 0)
            elif tgt == "PERIPH":
                if dwe: self.trace.append((daddr, dwdata))
                self.d_pending = (0, 0)
            elif tgt == "ACC":
                self.d_pending = (0, 0)
            elif tgt == "RM":
                if self.rm is None: self.d_pending = (0, 0)       # single-core build: register reads 0
                else:
                    if dwe: self.rm.sp_write(dwdata)
                    self.d_pending = (self.rm.sp, 0)
            else:
                self.d_pending = (0, 1)                        # default target: error response

# ----------------------------------------------------------------------------- recovery manager
MONITOR, SAVE, RESET, RESTORE, VERIFY, SAFE = "MONITOR", "SAVE", "RESET", "RESTORE", "VERIFY", "SAFE"

class RecoveryManager:
    def __init__(self, N=50, M=3, t_save=400, t_restore=400, reset_cycles=3):
        self.N, self.M, self.t_save, self.t_restore, self.reset_cycles = N, M, t_save, t_restore, reset_cycles
        self.state, self.sp, self.irq = MONITOR, 0, 0
        self.faulty, self.attempts, self.cnt = None, 0, 0
        self.sysreset_done = False            # fault history: survives system reset
        self.detections = self.recoveries = self.sysresets = 0
        self.t_detect = self.t_recovered = None
        self.core_reset = self.system_reset = False
        self.timeouts = []
        self._sp_event = None
    def sp_write(self, v): self.sp = v; self._sp_event = v
    def timeout_flag(self, tgt): self.timeouts.append(tgt)
    def _fail(self):
        self.attempts += 1
        if self.attempts >= self.M: self._escalate()
        elif self.sp != 0: self.state, self.cnt, self.irq = RESET, self.reset_cycles, 0   # state already saved: reset and reload
        else: self.state, self.cnt, self.irq = SAVE, 0, 1
    def _escalate(self):
        self.irq = 0
        if self.sysreset_done: self.state = SAFE
        else:
            self.sysreset_done, self.system_reset = True, True
            self.sysresets += 1
            self.state, self.sp, self.attempts, self.faulty = MONITOR, 0, 0, None
    def tick(self, flags, cycle):
        """Called once per cycle with the detector flags. Sets core_reset / system_reset / irq."""
        self.core_reset = self.system_reset = False
        ev, self._sp_event = self._sp_event, None
        n = sum(flags)
        if self.state == SAFE:
            self.core_reset = True; return
        if self.state == MONITOR:
            if n == 1:
                self.faulty, self.attempts = flags.index(True), 0
                self.detections += 1
                if self.t_detect is None: self.t_detect = cycle
                self.state, self.cnt, self.irq = SAVE, 0, 1
            elif n >= 2:
                self.detections += 1
                if self.t_detect is None: self.t_detect = cycle
                self._escalate()
        elif self.state == SAVE:
            others = [f for i, f in enumerate(flags) if i != self.faulty]
            self.cnt += 1
            if any(others): self._fail()
            elif ev: self.irq, self.state, self.cnt = 0, RESET, self.reset_cycles
            elif self.cnt > self.t_save: self._fail()
        elif self.state == RESET:
            self.core_reset = True
            self.cnt -= 1
            if self.cnt == 0: self.state, self.cnt = RESTORE, 0
        elif self.state == RESTORE:
            self.cnt += 1
            if n: self._fail()
            elif ev == 0: self.state, self.cnt = VERIFY, self.N
            elif self.cnt > self.t_restore: self._fail()
        elif self.state == VERIFY:
            if n: self._fail()
            else:
                self.cnt -= 1
                if self.cnt == 0:
                    self.recoveries += 1
                    self.t_recovered = cycle
                    self.state, self.faulty = MONITOR, None

# ----------------------------------------------------------------------------- system runs
def run_cluster(imem, handler, faults=(), permanent=None, max_cycles=60000, n_cores=3):
    """faults: list of (cycle, core, target, bit). Returns a result dict."""
    rm = RecoveryManager() if n_cores == 3 else None
    bus = Bus(imem, rm)
    cores = [Core(handler) for _ in range(n_cores)]
    if permanent is not None:
        cores[permanent[0]].stuck = permanent[1:]; cores[permanent[0]].apply_stuck()
    faults = sorted(faults)
    fi, t_inject, restarts = 0, None, 0
    for cyc in range(max_cycles):
        while fi < len(faults) and faults[fi][0] == cyc:
            _, c, tgt, bit = faults[fi]; cores[c].flip(tgt, bit); fi += 1
            if t_inject is None: t_inject = cyc
        irq = rm.irq if rm else 0
        vecs = [c.out(irq) for c in cores]
        if n_cores == 3:
            voted = vote(*vecs); flags = detect(vecs, voted)
        else:
            voted, flags = vecs[0], [False]
        i_resp, d_resp = bus.responses()
        bus.request(voted)
        if rm:
            rm.tick(flags, cyc)
            if rm.system_reset:
                for c in cores: c.reset()
                bus.drop_pending(); bus.trace.append("RESTART"); restarts += 1
                continue
            if rm.core_reset:
                for c in cores: c.reset()
                bus.drop_pending()
                if rm.state == SAFE: break
                continue
        for c in cores: c.step(irq, i_resp, d_resp)
        states = [c.state for c in cores]
        if n_cores == 1 and states[0] in (HALT, TRAP): break
        if n_cores == 3 and (rm.state == MONITOR) and sum(s == HALT for s in states) >= 2 and not any(flags):
            if all(v == 0 for v in vecs) or states.count(HALT) == 3: break
    return dict(bus=bus, rm=rm, cores=cores, cycles=cyc + 1, t_inject=t_inject, restarts=restarts)

def classify(res, golden_trace, golden_mem):
    bus, rm, cores = res["bus"], res["rm"], res["cores"]
    halted = [c.state == HALT for c in cores]
    mem_ok = bus.dmem[:(SAVE_AREA - DMEM_BASE) >> 2] == golden_mem
    tr = bus.trace
    if rm is None:                                               # unprotected single core
        if cores[0].state == TRAP: return "crash (bus error)"
        if not halted[0]: return "hang"
        return "correct" if (mem_ok and tr == golden_trace) else "SILENT DATA CORRUPTION"
    if rm.state == SAFE: return "safe state (FAULT pin)"
    if sum(halted) < 2: return "hang"
    if "RESTART" in tr:
        last = len(tr) - 1 - tr[::-1].index("RESTART")
        ok = mem_ok and tr[last + 1:] == golden_trace
        return "correct after system reset" if ok else "SILENT DATA CORRUPTION"
    if not (mem_ok and tr == golden_trace): return "SILENT DATA CORRUPTION"
    if rm.recoveries: return "correct, fault detected and recovered"
    if len(set(c.snapshot() for c in cores)) > 1: return "correct, fault latent (never reached an output)"
    return "correct, fault had no effect"

# ----------------------------------------------------------------------------- the checks
def line(): print("-" * 78)

def check1(rng):
    print("CHECK 1  Voter and discrepancy detector"); line()
    ok = all(vote(a, b, c) == (1 if a + b + c >= 2 else 0) for a in (0, 1) for b in (0, 1) for c in (0, 1))
    print(f"  1-bit truth table (8 rows) matches 2-of-3 majority ............ {'PASS' if ok else 'FAIL'}")
    bad_mask = bad_loc = 0; T = 20000
    for _ in range(T):
        g = rng.getrandbits(VEC_BITS); v = [g, g, g]; k = rng.randrange(3)
        e = 0
        for _b in range(rng.randint(1, VEC_BITS)): e |= 1 << rng.randrange(VEC_BITS)
        v[k] ^= e
        y = vote(*v); f = detect(v, y)
        bad_mask += y != g; bad_loc += f != [i == k for i in range(3)]
    print(f"  {T} random 103-bit vectors, 1 to 103 wrong bits in ONE core:")
    print(f"      voted output equals the correct value ..................... {T - bad_mask}/{T}")
    print(f"      detector flags exactly the faulty core .................... {T - bad_loc}/{T}")
    und = wrong = 0
    for _ in range(T):
        g = rng.getrandbits(VEC_BITS); v = [g, g, g]; a, b = rng.sample(range(3), 2)
        v[a] ^= 1 << rng.randrange(VEC_BITS); v[b] ^= 1 << rng.randrange(VEC_BITS)
        y = vote(*v); f = detect(v, y)
        und += sum(f) == 0; wrong += (y != g)
    print(f"  {T} cases with TWO cores wrong (1 bit each):")
    print(f"      detected (at least one flag raised) ....................... {T - und}/{T}")
    print(f"      voted output wrong (both hit the same bit) ................ {wrong}/{T}   <- outside the fault model")
    print()
    return ok and not bad_mask and not bad_loc

def check2(rng):
    print("CHECK 2  Address map and decoder"); line()
    nib = list(REGIONS)
    ok1 = len(nib) == len(set(nib))
    print(f"  Regions differ in address[31:28] ({', '.join(f'{REGIONS[n]}=0x{n:X}' for n in nib)}) ... {'PASS' if ok1 else 'FAIL'}")
    T = 200000; hit = Counter()
    for _ in range(T): hit[decode(rng.getrandbits(32))] += 1
    exp = {r: T / 16 for r in REGIONS.values()}
    print(f"  {T} random addresses: every address maps to exactly one region or to the error target")
    for r in REGIONS.values(): print(f"      {r:7s} {hit[r]:7d}   (expected about {exp[r]:.0f})")
    print(f"      error   {hit[None]:7d}   (expected about {T * 11 / 16:.0f})")
    bases = [(IMEM_BASE, "IMEM"), (DMEM_BASE, "DMEM"), (PERI_BASE, "PERIPH"), (ACC_BASE, "ACC"), (RM_BASE, "RM")]
    ok2 = all(decode(b) == n and decode(b + 0x0FFFFFFF) == n for b, n in bases)
    print(f"  First and last address of each region decode to that region ... {'PASS' if ok2 else 'FAIL'}")
    print()
    return ok1 and ok2

def check3():
    print("CHECK 3  PHX_BUS D-channel behaviour (scripted master)"); line()
    rm = RecoveryManager(); bus = Bus([("halt",)], rm, timeout=16)
    def xfer(addr, we=0, data=0, limit=64):
        bus.request(pack(0, 0, 1, we, 0xF, addr, data))
        for n in range(1, limit):
            _, d = bus.responses()
            if d is not None: return d[0], d[1], n
        return None, None, None
    res = []
    d, e, n = xfer(DMEM_BASE + 0x10, 1, 0xCAFEF00D); a = (e == 0 and n == 1)
    d, e, n2 = xfer(DMEM_BASE + 0x10); a &= (d == 0xCAFEF00D and e == 0 and n2 == 1)
    res.append(("Write then read DMEM: data returned, response 1 cycle after grant", a))
    d, e, n = xfer(0x9000_0000); res.append((f"Unmapped address: error response after {n} cycle", e == 1 and n == 1))
    bus.stuck.add("PERIPH")
    d, e, n = xfer(GPIO_ODR, 1, 1)
    res.append((f"Target stops answering: transfer ended with error after {n} cycles (limit 16), target reported to PHX_RM",
                e == 1 and n == 16 and rm.timeouts == ["PERIPH"]))
    d, e, n = xfer(DMEM_BASE + 0x10); res.append(("Other targets still work while one is stuck", e == 0 and d == 0xCAFEF00D))
    bus.stuck.discard("PERIPH")                                   # PHX_RM pulses the target reset
    d, e, n = xfer(GPIO_ODR, 1, 1); res.append(("After target reset the repeated access succeeds (known-good check)", e == 0 and n == 1))
    bus.stuck.add("PERIPH"); xfer(GPIO_ODR, 1, 1); bus.isolated.add("PERIPH")   # still broken -> isolate
    d, e, n = xfer(GPIO_ODR, 1, 1); res.append((f"Isolated target: immediate error ({n} cycle), no further timeouts", e == 1 and n == 1))
    d, e, n = xfer(DMEM_BASE + 0x10); res.append(("Rest of the system unaffected by the isolated target", e == 0))
    for s, ok in res: print(f"  {'PASS' if ok else 'FAIL'}  {s}")
    print()
    return all(ok for _, ok in res)

def campaign(rng, runs):
    imem, handler = build_program()
    g = run_cluster(imem, handler, n_cores=1)
    golden_trace, golden_mem = list(g["bus"].trace), g["bus"].dmem[:(SAVE_AREA - DMEM_BASE) >> 2]
    g3 = run_cluster(imem, handler)
    base_ok = classify(g3, golden_trace, golden_mem) == "correct, fault had no effect" and g3["cycles"] - g["cycles"] <= 2
    print("CHECK 4  Fault-injection campaign: three cores + voters + PHX_RM"); line()
    print(f"  Workload: {len(golden_trace)} writes to memory and peripherals, {g['cycles']} cycles fault-free")
    print(f"  Fault-free three-core run gives the same result, same cycle count  {'PASS' if base_ok else 'FAIL'}")
    faults = []
    for _ in range(runs):
        tgt = rng.choice(Core.TARGETS)
        faults.append((rng.randrange(20, g["cycles"] - 5), rng.randrange(3), tgt, rng.randrange(32)))
    out3, out1 = Counter(), Counter(); lat, rec = [], []; by_tgt = {}
    for f in faults:
        r = run_cluster(imem, handler, faults=[f])
        c = classify(r, golden_trace, golden_mem); out3[c] += 1
        by_tgt.setdefault(f[2], Counter())[c] += 1
        rm = r["rm"]
        if rm.t_detect is not None: lat.append(rm.t_detect - f[0])
        if rm.recoveries and rm.t_recovered is not None: rec.append(rm.t_recovered - rm.t_detect)
        r1 = run_cluster(imem, handler, faults=[(f[0], 0, f[2], f[3])], n_cores=1, max_cycles=20000)
        out1[classify(r1, golden_trace, golden_mem)] += 1
    print(f"  {runs} runs, one random bit flip per run (random cycle, core, register, bit)\n")
    print("  Outcome, protected cluster" + " " * 30 + "runs      %")
    for k, v in sorted(out3.items(), key=lambda x: -x[1]): print(f"      {k:52s}{v:6d}  {100 * v / runs:5.1f}")
    sdc3 = out3["SILENT DATA CORRUPTION"] + out3["hang"]
    print(f"\n  Wrong results or hangs in the protected cluster: {sdc3}")
    if lat:
        ls = sorted(lat)
        print(f"  Detection latency (cycles from flip to flag): median {statistics.median(ls):.0f}, "
              f"90th percentile {ls[int(0.9 * len(ls))]}, max {ls[-1]}")
    if rec:
        print(f"  Recovery time (flag to verified, includes the N = 50 check): min {min(rec)}, median {statistics.median(rec):.0f}, max {max(rec)} cycles")
    print("  (cycle counts are for the toy core in this model, not for Ibex)\n")
    print("  Outcome by where the flip landed (protected cluster)")
    cols = ["detected+recovered", "latent", "no effect", "other"]
    print("      target   " + "".join(f"{c:>20s}" for c in cols))
    for tgt in Core.TARGETS:
        c = by_tgt.get(tgt, Counter()); tot = sum(c.values())
        a = c["correct, fault detected and recovered"]; b = c["correct, fault latent (never reached an output)"]
        d = c["correct, fault had no effect"]
        print(f"      {tgt:8s} " + "".join(f"{x:20d}" for x in (a, b, d, tot - a - b - d)))
    print()
    print("CHECK 5  The same faults on ONE unprotected core"); line()
    print("  Outcome, single core" + " " * 36 + "runs      %")
    for k, v in sorted(out1.items(), key=lambda x: -x[1]): print(f"      {k:52s}{v:6d}  {100 * v / runs:5.1f}")
    bad1 = runs - out1["correct"]
    print(f"\n  Runs that end wrong, crashed or hung:  single core {bad1} ({100 * bad1 / runs:.1f}%)   protected cluster {sdc3}")
    print()
    return base_ok and sdc3 == 0, (imem, handler, golden_trace, golden_mem, g["cycles"])

def check6(rng, ctx, runs):
    imem, handler, gt, gm, gc = ctx
    print("CHECK 6  Escalation"); line()
    out = Counter(); maxres = 0
    for _ in range(40):
        r = run_cluster(imem, handler, permanent=(rng.randrange(3), "pc", rng.choice([3, 4, 5, 9, 13, 20])))
        out[classify(r, gt, gm)] += 1; maxres = max(maxres, r["rm"].sysresets)
    ok_a = out["safe state (FAULT pin)"] == 40 and maxres == 1
    print("  (a) Permanent fault in one core (a program-counter bit stuck at 1), 40 runs")
    for k, v in out.items(): print(f"        {k:50s}{v:5d}")
    print(f"        system resets per run: at most {maxres}  -> no endless reset loop ......... {'PASS' if ok_a else 'FAIL'}")
    out = Counter(); n = max(200, runs // 5)
    for _ in range(n):
        t = rng.randrange(20, gc - 5); a, b = rng.sample(range(3), 2)
        fs = [(t, a, rng.choice(Core.TARGETS), rng.randrange(32)), (t + rng.randrange(0, 3), b, rng.choice(Core.TARGETS), rng.randrange(32))]
        out[classify(run_cluster(imem, handler, faults=fs), gt, gm)] += 1
    bad = out["SILENT DATA CORRUPTION"] + out["hang"]
    print(f"\n  (b) Two different cores hit within 3 cycles (outside the single-fault model), {n} runs")
    for k, v in sorted(out.items(), key=lambda x: -x[1]): print(f"        {k:50s}{v:5d}  {100 * v / n:5.1f}%")
    print(f"        wrong results or hangs: {bad}")
    print()
    return ok_a, bad

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    print("=" * 78)
    print("PHOENIX SoC  -  PRE-RTL ARCHITECTURE MODEL  -  results")
    print(f"seed {a.seed}, {a.runs} fault-injection runs")
    print("=" * 78); print()
    r1 = check1(rng); r2 = check2(rng); r3 = check3()
    r4, ctx = campaign(rng, a.runs)
    r6a, bad6 = check6(rng, ctx, a.runs)
    print("=" * 78); print("SUMMARY")
    for name, ok in [("1 Voter and detector", r1), ("2 Address map", r2), ("3 Bus behaviour", r3),
                     ("4 Single-fault campaign: no wrong result, no hang", r4), ("6a Permanent fault ends in safe state", r6a)]:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"  INFO  6b Double faults: {bad6} wrong results or hangs (not required to be zero)")
    print("=" * 78)
    sys.exit(0 if all([r1, r2, r3, r4, r6a]) else 1)

if __name__ == "__main__":
    main()
