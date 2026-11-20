#!/usr/bin/env python3
"""
Phoenix SoC - pre-RTL architecture model, version 2
===================================================
Cycle-level executable model of the Phoenix architecture, used to test the LOGIC of the
architecture before RTL exists. Version 2 adds three protection mechanisms and a larger,
wider fault campaign, and runs every experiment twice: BEFORE (mechanisms off) and AFTER
(mechanisms on).

  Mechanism 1  Periodic resynchronisation ("scrub"): PHX_RM forces a save / reset / restore
               every SCRUB_PERIOD cycles, so a hidden wrong bit in one core is found and cleared.
  Mechanism 2  Watchdog: software must write to a PHX_RM register regularly; if it stops,
               PHX_RM performs a system reset.
  Mechanism 3  SECDED error-correcting code on data memory: 32 data bits + 7 check bits;
               corrects any 1 wrong bit in a word, detects any 2.

What the model is NOT: it does not contain Ibex, gates, voltages or real timing. The "core"
is a small register machine with the same kind of ports as Ibex (fetch port, data port,
interrupt, reset). Cycle counts apply to this toy core only.

Run:   python3 phoenix_model_v2.py                 full campaign, writes results_v2.json
       python3 phoenix_model_v2.py --scale 0.1     quick run with one tenth of the cases
"""
import argparse, json, random, statistics, sys, time
from collections import Counter
from multiprocessing import Pool

M32 = 0xFFFFFFFF

# ============================================================================ address map
IMEM_BASE, DMEM_BASE, PERI_BASE, ACC_BASE, RM_BASE = 0x0000_0000, 0x2000_0000, 0x4000_0000, 0x5000_0000, 0xE000_0000
REGIONS = {0x0: "IMEM", 0x2: "DMEM", 0x4: "PERIPH", 0x5: "ACC", 0xE: "RM"}
GPIO_ODR, UART_TX = PERI_BASE + 0x0000, PERI_BASE + 0x3000      # example slots (model only)
RM_SP, RM_WDT = RM_BASE, RM_BASE + 4                            # PHX_RM registers used by the model
DMEM_WORDS = 1024
SAVE_AREA, RESULT = DMEM_BASE + 0xF00, DMEM_BASE + 0x800
N_ITER = 60
APP_WORDS = (SAVE_AREA - DMEM_BASE) >> 2

def decode(addr):
    return REGIONS.get((addr >> 28) & 0xF)

# ============================================================================ voter / detector
def pack(ireq, iaddr, dreq, dwe, dbe, daddr, dwdata):          # 103-bit bus-output vector
    v = ireq & 1
    v = (v << 32) | (iaddr & M32)
    v = (v << 1) | (dreq & 1)
    v = (v << 1) | (dwe & 1)
    v = (v << 4) | (dbe & 0xF)
    v = (v << 32) | (daddr & M32)
    return (v << 32) | (dwdata & M32)

def unpack(v):
    dwdata = v & M32; v >>= 32
    daddr = v & M32; v >>= 32
    dbe = v & 0xF; v >>= 4
    dwe = v & 1; v >>= 1
    dreq = v & 1; v >>= 1
    iaddr = v & M32; v >>= 32
    return (v & 1, iaddr, dreq, dwe, dbe, daddr, dwdata)

VEC_BITS = 103
def vote(a, b, c): return (a & b) | (b & c) | (a & c)          # Y = A.B + B.C + A.C
def detect(vecs, voted): return [v != voted for v in vecs]

# ============================================================================ SECDED (39,32)
# Extended Hamming code. Positions 1..38 hold 32 data bits and 6 check bits (the check bits
# sit at positions 1,2,4,8,16,32). Bit 0 is an overall parity bit over the other 38.
DATA_POS = [p for p in range(1, 39) if p & (p - 1)]            # 32 positions that are not powers of two
def ecc_encode(d):
    cw = 0
    for i, p in enumerate(DATA_POS):
        if (d >> i) & 1: cw |= 1 << p
    for k in range(6):                                         # check bit k covers positions with bit k set
        par = 0
        for p in range(1, 39):
            if (p >> k) & 1 and (cw >> p) & 1: par ^= 1
        if par: cw |= 1 << (1 << k)
    if bin(cw).count("1") & 1: cw |= 1                         # overall parity -> even weight
    return cw

def ecc_decode(cw):
    """Returns (data, status): 0 = clean, 1 = one bit corrected, 2 = uncorrectable."""
    syn = 0
    for p in range(1, 39):
        if (cw >> p) & 1: syn ^= p
    odd = bin(cw).count("1") & 1
    status = 0
    if odd:                                                    # odd number of wrong bits: assume one
        if syn > 38: return 0, 2
        cw ^= 1 << syn                                         # syn == 0 -> the parity bit itself
        status = 1
    elif syn: return 0, 2                                      # even weight but non-zero syndrome: two wrong bits
    d = 0
    for i, p in enumerate(DATA_POS):
        if (cw >> p) & 1: d |= 1 << i
    return d, status

# ============================================================================ toy program
def build_program(n_iter=N_ITER):
    P = {}
    def put(addr, *ins):
        for i, x in enumerate(ins): P[addr + 4 * i] = x
    APP, RESTORE, HANDLER = 0x40, 0x100, 0x180
    put(0x00, ("li", 1, RM_SP), ("ld", 2, 1, 0), ("bne", 2, 0, RESTORE), ("jmp", APP))
    put(APP,
        ("ei",), ("li", 1, 0), ("li", 2, 0), ("li", 3, n_iter), ("li", 4, DMEM_BASE),
        ("li", 5, 0), ("li", 7, GPIO_ODR),
        # loop @ APP+28
        ("addi", 1, 1, 1), ("add", 2, 2, 1), ("st", 2, 4, 0), ("ld", 6, 4, 0), ("add", 5, 5, 6),
        ("st", 1, 7, 0), ("st", 0, 0, RM_WDT),                 # GPIO write, then kick the watchdog
        ("addi", 4, 4, 4), ("bne", 1, 3, APP + 28),
        # second pass: read the whole array back and add it up (so stored data is used again)
        ("li", 4, DMEM_BASE), ("li", 1, 0), ("li", 5, 0),
        # loop2 @ APP+76
        ("ld", 6, 4, 0), ("add", 5, 5, 6), ("st", 0, 0, RM_WDT), ("addi", 4, 4, 4), ("addi", 1, 1, 1),
        ("bne", 1, 3, APP + 76),
        ("li", 4, RESULT), ("st", 2, 4, 0), ("st", 5, 4, 4), ("li", 6, UART_TX), ("st", 5, 6, 0),
        ("halt",))
    h = [("st", r, 0, SAVE_AREA + 4 * r) for r in range(1, 8)]
    h += [("csrr", 1), ("st", 1, 0, SAVE_AREA + 32), ("li", 1, SAVE_AREA), ("st", 1, 0, RM_SP),
          ("jmp", HANDLER + 4 * 11)]
    put(HANDLER, *h)
    r = [("ld", 1, 2, 32), ("csrw", 1)] + [("ld", k, 2, 4 * k) for k in range(3, 8)]
    r += [("st", 0, 0, RM_SP), ("ld", 1, 2, 4), ("ld", 2, 2, 8), ("mret",)]
    put(RESTORE, *r)
    size = max(P) // 4 + 1
    return [P.get(4 * i, ("halt",)) for i in range(size)], HANDLER

# ============================================================================ toy core
F_REQ, F_WAIT, EX, D_WAIT, HALT, TRAP = range(6)
CORE_TARGETS = ["pc", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "mepc", "ie", "state"]

class Core:
    def __init__(self, handler):
        self.handler, self.stuck = handler, None
        self.reset()
    def reset(self):
        self.pc, self.mepc, self.ie, self.state = 0, 0, 0, F_REQ
        self.r, self.ir = [0] * 8, None
        self.apply_stuck()
    def apply_stuck(self):
        if self.stuck: self.pc |= (1 << self.stuck)
    def out(self, irq):
        if self.state == F_REQ and not (irq and self.ie):
            return pack(1, self.pc, 0, 0, 0, 0, 0)
        if self.state == EX and self.ir is not None and self.ir[0] in ("ld", "st"):
            op = self.ir; addr = (self.r[op[2]] + op[3]) & M32
            if op[0] == "st": return pack(0, 0, 1, 1, 0xF, addr, self.r[op[1]])
            return pack(0, 0, 1, 0, 0xF, addr, 0)
        return 0
    def step(self, irq, i_resp, d_resp):
        s = self.state
        if s == F_REQ:
            if irq and self.ie: self.mepc, self.ie, self.pc = self.pc, 0, self.handler
            else: self.state = F_WAIT
        elif s == F_WAIT:
            if i_resp is not None:
                data, err = i_resp
                if err or data is None: self.state = TRAP
                else: self.ir, self.state = data, EX
        elif s == EX and self.ir is None:
            self.state = TRAP                                  # no instruction latched: illegal state
        elif s == EX:
            op = self.ir; k = op[0]; nxt = (self.pc + 4) & M32
            if k in ("ld", "st"): self.state = D_WAIT
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
                if self.state == EX: self.pc, self.state = nxt, F_REQ
        elif s == D_WAIT and self.ir is None:
            self.state = TRAP
        elif s == D_WAIT:
            if d_resp is not None:
                data, err = d_resp
                if err: self.state = TRAP
                else:
                    if self.ir[0] == "ld": self.r[self.ir[1]] = data & M32
                    self.r[0] = 0
                    self.pc, self.state = (self.pc + 4) & M32, F_REQ
        self.apply_stuck()
    def flip(self, target, bit):
        if target == "pc": self.pc ^= 1 << bit
        elif target == "mepc": self.mepc ^= 1 << bit
        elif target == "ie": self.ie ^= 1
        elif target == "state": self.state = (self.state ^ (1 << (bit % 2))) % 4
        else: self.r[int(target[1])] ^= 1 << bit
    def snapshot(self): return (self.pc, self.mepc, self.ie, self.state, tuple(self.r))

# ============================================================================ bus + targets
class Bus:
    def __init__(self, imem, rm=None, timeout=16, ecc=False):
        self.imem, self.rm, self.timeout, self.ecc = imem, rm, timeout, ecc
        self.dmem = [ecc_encode(0) if ecc else 0] * DMEM_WORDS
        self.i_pending = self.d_pending = self.d_wait = None
        self.trace = []
        self.ecc_corrected = self.ecc_uncorrectable = 0
    def drop_pending(self): self.i_pending = self.d_pending = self.d_wait = None
    def responses(self):
        i, d = self.i_pending, self.d_pending
        self.i_pending = self.d_pending = None
        return i, d
    def flip_mem(self, idx, bit): self.dmem[idx] ^= 1 << bit
    def mem_values(self):
        """Application memory as software would read it (ECC applied when enabled)."""
        if not self.ecc: return self.dmem[:APP_WORDS], 0, 0
        vals, fixed, bad = [], 0, 0
        for cw in self.dmem[:APP_WORDS]:
            d, st = ecc_decode(cw); vals.append(d if st < 2 else None)
            fixed += st == 1; bad += st == 2
        return vals, fixed, bad
    def request(self, voted):
        ireq, iaddr, dreq, dwe, dbe, daddr, dwdata = unpack(voted)
        if ireq:
            idx = iaddr >> 2
            ok = decode(iaddr) == "IMEM" and iaddr % 4 == 0 and idx < len(self.imem)
            self.i_pending = (self.imem[idx], 0) if ok else (None, 1)
        if dreq:
            tgt = decode(daddr)
            if tgt == "DMEM":
                idx = (daddr - DMEM_BASE) >> 2
                if idx >= DMEM_WORDS: self.d_pending = (0, 1)
                elif dwe:
                    self.dmem[idx] = ecc_encode(dwdata) if self.ecc else dwdata
                    if daddr < SAVE_AREA: self.trace.append((daddr, dwdata))
                    self.d_pending = (0, 0)
                elif self.ecc:
                    d, st = ecc_decode(self.dmem[idx])
                    if st == 2:
                        self.ecc_uncorrectable += 1; self.d_pending = (0, 1)   # error response
                    else:
                        if st == 1:
                            self.ecc_corrected += 1; self.dmem[idx] = ecc_encode(d)   # write the fix back
                        self.d_pending = (d, 0)
                else: self.d_pending = (self.dmem[idx], 0)
            elif tgt == "PERIPH":
                if dwe: self.trace.append((daddr, dwdata))
                self.d_pending = (0, 0)
            elif tgt == "ACC": self.d_pending = (0, 0)
            elif tgt == "RM":
                if self.rm is None: self.d_pending = (0, 0)
                else:
                    if dwe:
                        if daddr == RM_SP: self.rm.sp_write(dwdata)
                        elif daddr == RM_WDT: self.rm.kick()
                    self.d_pending = (self.rm.sp if daddr == RM_SP else 0, 0)
            else: self.d_pending = (0, 1)

# ============================================================================ recovery manager
MONITOR, SAVE, RESET, RESTORE, VERIFY, SAFE = "MONITOR", "SAVE", "RESET", "RESTORE", "VERIFY", "SAFE"

class RecoveryManager:
    def __init__(self, N=50, M=3, t_save=400, t_restore=400, reset_cycles=3, scrub=0, wdt=0):
        self.N, self.M, self.t_save, self.t_restore, self.reset_cycles = N, M, t_save, t_restore, reset_cycles
        self.scrub_period, self.wdt_limit = scrub, wdt
        self.state, self.sp, self.irq = MONITOR, 0, 0
        self.faulty, self.attempts, self.cnt = None, 0, 0
        self.sysreset_done = False
        self.detections = self.recoveries = self.sysresets = self.scrubs = self.wdt_fired = 0
        self.t_detect = self.t_recovered = None
        self.core_reset = self.system_reset = False
        self._sp_event = None
        self.scrub_cnt = self.wdt_cnt = 0
        self.is_scrub = False
    def sp_write(self, v): self.sp = v; self._sp_event = v
    def kick(self): self.wdt_cnt = 0
    def _fail(self):
        self.attempts += 1
        if self.attempts >= self.M: self._escalate()
        elif self.sp != 0: self.state, self.cnt, self.irq = RESET, self.reset_cycles, 0
        else: self.state, self.cnt, self.irq = SAVE, 0, 1
    def _escalate(self):
        self.irq = 0
        if self.sysreset_done: self.state = SAFE
        else:
            self.sysreset_done, self.system_reset = True, True
            self.sysresets += 1
            self.state, self.sp, self.attempts, self.faulty = MONITOR, 0, 0, None
            self.scrub_cnt = self.wdt_cnt = 0
    def _found(self, idx, cycle):
        self.faulty = idx; self.detections += 1
        if self.t_detect is None: self.t_detect = cycle
    def tick(self, flags, cycle):
        self.core_reset = self.system_reset = False
        ev, self._sp_event = self._sp_event, None
        n = sum(flags)
        if self.state == SAFE: self.core_reset = True; return
        if self.state == MONITOR:
            self.scrub_cnt += 1; self.wdt_cnt += 1
            if n == 1:
                self._found(flags.index(True), cycle); self.attempts, self.is_scrub = 0, False
                self.state, self.cnt, self.irq = SAVE, 0, 1
            elif n >= 2:
                self.detections += 1
                if self.t_detect is None: self.t_detect = cycle
                self._escalate()
            elif self.wdt_limit and self.wdt_cnt > self.wdt_limit:        # watchdog expired
                self.wdt_fired += 1; self._escalate()
            elif self.scrub_period and self.scrub_cnt >= self.scrub_period:   # periodic resynchronisation
                self.faulty, self.attempts, self.is_scrub = None, 0, True
                self.scrubs += 1
                self.state, self.cnt, self.irq = SAVE, 0, 1
        elif self.state == SAVE:
            self.cnt += 1
            if self.faulty is None and n == 1: self._found(flags.index(True), cycle)   # scrub exposed a hidden fault
            others = [f for i, f in enumerate(flags) if i != self.faulty]
            if any(others): self._fail()
            elif ev: self.irq, self.state, self.cnt = 0, RESET, self.reset_cycles
            elif self.cnt > self.t_save: self._fail()
        elif self.state == RESET:
            self.core_reset = True; self.cnt -= 1
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
                    if self.faulty is not None:
                        self.recoveries += 1; self.t_recovered = cycle
                    self.state, self.faulty = MONITOR, None
                    self.scrub_cnt = self.wdt_cnt = 0

# ============================================================================ one run
BEFORE = dict(scrub=0, wdt=0, ecc=False)
AFTER = dict(scrub=400, wdt=300, ecc=True)
_PROG = build_program()

def run(faults=(), cfg=BEFORE, n_cores=3, permanent=None, max_cycles=40000):
    """faults: list of (cycle, 'core', core, target, bit) or (cycle, 'mem', word, bit)."""
    imem, handler = _PROG
    rm = RecoveryManager(scrub=cfg["scrub"], wdt=cfg["wdt"]) if n_cores == 3 else None
    bus = Bus(imem, rm, ecc=cfg["ecc"])
    cores = [Core(handler) for _ in range(n_cores)]
    if permanent is not None:
        cores[permanent[0]].stuck = permanent[1]; cores[permanent[0]].apply_stuck()
    faults = sorted(faults); fi = 0
    for cyc in range(max_cycles):
        while fi < len(faults) and faults[fi][0] == cyc:
            f = faults[fi]; fi += 1
            if f[1] == "core": cores[f[2] % n_cores].flip(f[3], f[4])
            else: bus.flip_mem(f[2], f[3])
        irq = rm.irq if rm else 0
        vecs = [c.out(irq) for c in cores]
        if n_cores == 3:
            voted = vote(*vecs); flags = detect(vecs, voted)
        else: voted, flags = vecs[0], [False]
        i_resp, d_resp = bus.responses()
        bus.request(voted)
        if rm:
            rm.tick(flags, cyc)
            if rm.system_reset:
                for c in cores: c.reset()
                bus.drop_pending(); bus.trace.append("RESTART"); continue
            if rm.core_reset:
                for c in cores: c.reset()
                bus.drop_pending()
                if rm.state == SAFE: break
                continue
        for c in cores: c.step(irq, i_resp, d_resp)
        st = [c.state for c in cores]
        if n_cores == 1:
            if st[0] in (HALT, TRAP): break
        else:
            idle = rm.state == MONITOR or (rm.state == SAVE and rm.cnt <= 1 and rm.is_scrub)
            if idle and st.count(HALT) >= 2 and not any(flags): break
            if not rm.wdt_limit and rm.state == MONITOR and st.count(TRAP) >= 2: break   # nothing will ever rescue it
    return bus, rm, cores, cyc + 1

_G = None
def golden():
    global _G
    if _G is None:
        bus, _, _, cyc = run(n_cores=1)
        _G = (list(bus.trace), bus.dmem[:APP_WORDS], cyc)
    return _G

# outcome labels
REC, ECC, RST, SAFE_O, NOEFF, DUE, LAT, WRONG, HANG, CRASH = (
    "Detected and recovered", "Corrected by memory ECC", "Correct after system reset", "Safe state",
    "No effect (overwritten or cleared)", "Flagged by ECC, not correctable", "Latent (hidden, not cleared)",
    "Wrong result", "Hang", "Crash")
ORDER = [REC, ECC, NOEFF, RST, SAFE_O, DUE, LAT, WRONG, HANG, CRASH]

def classify(bus, rm, cores):
    gt, gm, _ = golden()
    vals, fixed_at_end, bad = bus.mem_values()
    mem_ok = vals == gm
    tr = bus.trace
    halted = [c.state == HALT for c in cores]
    if rm is None:
        if cores[0].state == TRAP: return CRASH
        if not halted[0]: return HANG
        return NOEFF if (mem_ok and tr == gt) else WRONG
    if rm.state == SAFE: return SAFE_O
    if sum(halted) < 2: return HANG
    if "RESTART" in tr:
        last = len(tr) - 1 - tr[::-1].index("RESTART")
        return RST if (mem_ok and tr[last + 1:] == gt) else WRONG
    if tr == gt and bad and all(v is None or v == g for v, g in zip(vals, gm)):
        return DUE                      # a word holds 2 wrong bits; ECC flags it and no wrong value was ever used
    if not (mem_ok and tr == gt): return WRONG
    if rm.recoveries: return REC
    if bus.ecc_corrected or fixed_at_end: return ECC
    if len(set(c.snapshot() for c in cores)) > 1: return LAT
    return NOEFF

# ============================================================================ campaign workers
def _job(args):
    kind, faults, cfgname, perm = args
    cfg = AFTER if cfgname == "after" else BEFORE if cfgname == "before" else cfgname
    if kind == "single":
        bus, rm, cores, cyc = run(faults, BEFORE, n_cores=1, max_cycles=12000)
        return classify(bus, rm, cores), None, None, cyc, None
    bus, rm, cores, cyc = run(faults, cfg, permanent=perm)
    t0 = min(f[0] for f in faults) if faults else None
    lat = (rm.t_detect - t0) if (rm.t_detect is not None and t0 is not None) else None
    rec = (rm.t_recovered - rm.t_detect) if (rm.recoveries and rm.t_recovered is not None and rm.t_detect is not None) else None
    return classify(bus, rm, cores), lat, rec, cyc, faults[0][3] if (faults and faults[0][1] == "core") else None

def make_faults(rng, kind, n, cyc):
    used = list(range(N_ITER)) + [(RESULT - DMEM_BASE) >> 2, ((RESULT - DMEM_BASE) >> 2) + 1]
    out = []
    for _ in range(n):
        t = rng.randrange(20, cyc - 5)
        if kind == "core":
            out.append([(t, "core", rng.randrange(3), rng.choice(CORE_TARGETS), rng.randrange(32))])
        elif kind == "mem1":
            out.append([(t, "mem", rng.choice(used[:N_ITER]), rng.randrange(32))])
        elif kind == "mem2":
            w = rng.choice(used[:N_ITER]); b1, b2 = rng.sample(range(32), 2)
            out.append([(t, "mem", w, b1), (t, "mem", w, b2)])
        elif kind == "dbl_near":
            a, b = rng.sample(range(3), 2)
            out.append([(t, "core", a, rng.choice(CORE_TARGETS), rng.randrange(32)),
                        (t + rng.randrange(0, 3), "core", b, rng.choice(CORE_TARGETS), rng.randrange(32))])
        elif kind == "dbl_far":
            a, b = rng.sample(range(3), 2)
            t2 = rng.randrange(20, cyc - 5)
            out.append([(t, "core", a, rng.choice(CORE_TARGETS), rng.randrange(32)),
                        (t2, "core", b, rng.choice(CORE_TARGETS), rng.randrange(32))])
    return out

def summarise(res):
    c = Counter(r[0] for r in res); n = len(res)
    lat = sorted(r[1] for r in res if r[1] is not None)
    rec = sorted(r[2] for r in res if r[2] is not None)
    d = dict(n=n, counts={k: c.get(k, 0) for k in ORDER if c.get(k, 0)},
             mean_cycles=statistics.mean(r[3] for r in res))
    if lat:
        d["latency"] = dict(n=len(lat), median=statistics.median(lat), p90=lat[int(0.9 * len(lat))],
                            p99=lat[int(0.99 * len(lat))], max=lat[-1])
        edges = [0, 10, 25, 50, 100, 200, 400, 800, 1600, 10 ** 9]
        d["latency_hist"] = [sum(1 for x in lat if edges[i] <= x < edges[i + 1]) for i in range(len(edges) - 1)]
        d["latency_edges"] = edges[:-1]
    if rec: d["recovery"] = dict(min=rec[0], median=statistics.median(rec), max=rec[-1])
    bt = {}
    for r in res:
        if r[4]: bt.setdefault(r[4], Counter())[r[0]] += 1
    if bt: d["by_target"] = {t: dict(v) for t, v in bt.items()}
    return d

def static_checks(rng):
    out = {}
    out["voter_truth_table"] = all(vote(a, b, c) == (1 if a + b + c >= 2 else 0) for a in (0, 1) for b in (0, 1) for c in (0, 1))
    T = 100000; bm = bl = 0
    for _ in range(T):
        g = rng.getrandbits(VEC_BITS); v = [g, g, g]; k = rng.randrange(3); e = 0
        for _b in range(rng.randint(1, VEC_BITS)): e |= 1 << rng.randrange(VEC_BITS)
        v[k] ^= e; y = vote(*v)
        bm += y != g; bl += detect(v, y) != [i == k for i in range(3)]
    out["voter_single"] = dict(trials=T, masked=T - bm, located=T - bl)
    T2 = 200000; hit = Counter(decode(rng.getrandbits(32)) for _ in range(T2))
    out["decode"] = dict(trials=T2, hits={str(k): v for k, v in hit.items()})
    # SECDED: every single-bit and every double-bit error pattern, on many random words
    words = 300; s_ok = d_ok = s_tot = d_tot = clean = 0
    for _ in range(words):
        d = rng.getrandbits(32); cw = ecc_encode(d)
        clean += ecc_decode(cw) == (d, 0)
        for i in range(39):
            s_tot += 1; s_ok += ecc_decode(cw ^ (1 << i)) == (d, 1)
            for j in range(i + 1, 39):
                d_tot += 1; d_ok += ecc_decode(cw ^ (1 << i) ^ (1 << j))[1] == 2
    out["ecc"] = dict(words=words, clean=clean, single_total=s_tot, single_corrected=s_ok, double_total=d_tot, double_detected=d_ok)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default="results_v2.json")
    a = ap.parse_args()
    rng = random.Random(a.seed); t0 = time.time()
    gt, gm, gcyc = golden()
    S = lambda n: max(40, int(n * a.scale))
    plan = [("core", "One bit flip in one core", S(20000)), ("mem1", "One bit flip in a data-memory word", S(8000)),
            ("mem2", "Two bit flips in one data-memory word", S(2000)),
            ("dbl_far", "Two cores hit at independent times", S(6000)), ("dbl_near", "Two cores hit within 3 cycles", S(6000))]
    R = dict(seed=a.seed, golden_cycles=gcyc, golden_writes=len(gt), before_cfg=BEFORE, after_cfg=AFTER,
             static=static_checks(rng), experiments={}, order=ORDER)
    # fault-free cost of the mechanisms
    R["fault_free"] = {}
    for name, cfg in (("before", BEFORE), ("after", AFTER)):
        bus, rm, cores, cyc = run(cfg=cfg)
        R["fault_free"][name] = dict(cycles=cyc, outcome=classify(bus, rm, cores), scrubs=rm.scrubs)
    with Pool() as pool:
        for kind, label, n in plan:
            fl = make_faults(rng, kind, n, gcyc)
            e = dict(label=label, n=n)
            for cfgname in ("before", "after"):
                e[cfgname] = summarise(pool.map(_job, [("tmr", f, cfgname, None) for f in fl], chunksize=64))
            if kind in ("core", "mem1"):
                e["single_core"] = summarise(pool.map(_job, [("single", f, "before", None) for f in fl], chunksize=64))
            R["experiments"][kind] = e
            print(f"[{time.time() - t0:6.0f}s] {label}: {n} cases done", flush=True)
        # permanent fault
        n = S(400); perms = [(rng.randrange(3), rng.choice([3, 4, 5, 9, 13, 20])) for _ in range(n)]
        e = dict(label="Permanent fault in one core", n=n)
        for cfgname in ("before", "after"):
            e[cfgname] = summarise(pool.map(_job, [("tmr", [], cfgname, p) for p in perms], chunksize=16))
        R["experiments"]["perm"] = e
        # scrub-period sweep on single core faults
        fl = make_faults(rng, "core", S(4000), gcyc); sweep = []
        for period in (0, 800, 400, 200, 100, 50):
            cfg = dict(scrub=period, wdt=300, ecc=True)
            s = summarise(pool.map(_job, [("tmr", f, cfg, None) for f in fl], chunksize=64))
            bus, rm, cores, cyc = run(cfg=cfg)
            sweep.append(dict(period=period, counts=s["counts"], n=s["n"], fault_free_cycles=cyc,
                              latency=s.get("latency"), overhead=(cyc - gcyc) / gcyc))
        R["scrub_sweep"] = sweep
        print(f"[{time.time() - t0:6.0f}s] permanent faults and scrub sweep done", flush=True)
    R["total_runs"] = sum(e["n"] * (3 if "single_core" in e else 2) for e in R["experiments"].values()) + 6 * S(4000)
    R["seconds"] = round(time.time() - t0)
    json.dump(R, open(a.out, "w"), indent=1)
    print("\nwrote", a.out, "| total simulated runs:", R["total_runs"])
    for k, e in R["experiments"].items():
        print(f"\n{e['label']}  (n = {e['n']})")
        for cfgname in ("single_core", "before", "after"):
            if cfgname in e:
                c = e[cfgname]["counts"]
                print(f"   {cfgname:11s} " + ", ".join(f"{k2}: {100 * v / e['n']:.1f}%" for k2, v in c.items()))

if __name__ == "__main__":
    main()
