#!/usr/bin/env python3
"""Exports the exact fault lists used by phoenix_model_v2.py (seed 2026, scale 0.5) and the
Python outcome of every run, so the MATLAB port can replay the same cases and be compared run by run.

Outcome codes: 1 Detected and recovered, 2 Corrected by ECC, 3 No effect, 4 Correct after system reset,
5 Safe state, 6 Flagged by ECC not correctable, 7 Latent, 8 Wrong result, 9 Hang, 10 Crash."""
import csv, os, random, sys
from multiprocessing import Pool
import phoenix_model_v2 as m

OUT = sys.argv[1] if len(sys.argv) > 1 else "matlab_data"
SCALE, SEED = 0.5, 2026
os.makedirs(OUT, exist_ok=True)
S = lambda n: max(40, int(n * SCALE))
CODE = {lab: i + 1 for i, lab in enumerate(m.ORDER)}
TGT = {t: i + 1 for i, t in enumerate(m.CORE_TARGETS)}

def job(args):
    kind, faults, cfg, perm = args
    r = m._job((kind, faults, cfg, perm))
    return CODE[r[0]], (-1 if r[1] is None else r[1]), (-1 if r[2] is None else r[2]), r[3]

def write_faults(name, fl):
    with open(f"{OUT}/faults_{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["run", "cycle", "type", "unit", "target", "bit"])
        for i, faults in enumerate(fl, 1):
            for x in faults:
                if x[1] == "core": w.writerow([i, x[0], 1, x[2], TGT[x[3]], x[4]])
                else: w.writerow([i, x[0], 2, x[2], 0, x[3]])

def write_out(name, res):
    with open(f"{OUT}/python_{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["run", "outcome", "latency", "recovery", "cycles"])
        for i, r in enumerate(res, 1): w.writerow([i, *r])

def main():
    rng = random.Random(SEED)
    gt, gm, gcyc = m.golden()
    m.static_checks(rng)                                   # consumes the generator exactly as main() does
    plan = [("core", S(20000)), ("mem1", S(8000)), ("mem2", S(2000)), ("dbl_far", S(6000)), ("dbl_near", S(6000))]
    with Pool() as pool:
        for kind, n in plan:
            fl = m.make_faults(rng, kind, n, gcyc)
            write_faults(kind, fl)
            for cfg in ("before", "after"):
                write_out(f"{kind}_{cfg}", pool.map(job, [("tmr", f, cfg, None) for f in fl], chunksize=64))
            if kind in ("core", "mem1"):
                write_out(f"{kind}_single", pool.map(job, [("single", f, "before", None) for f in fl], chunksize=64))
            print(kind, n, flush=True)
        n = S(400); perms = [(rng.randrange(3), rng.choice([3, 4, 5, 9, 13, 20])) for _ in range(n)]
        with open(f"{OUT}/faults_perm.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["run", "core", "bit"])
            for i, p in enumerate(perms, 1): w.writerow([i, *p])
        for cfg in ("before", "after"):
            write_out(f"perm_{cfg}", pool.map(job, [("tmr", [], cfg, p) for p in perms], chunksize=16))
        fl = m.make_faults(rng, "core", S(4000), gcyc)
        write_faults("sweep", fl)
        for period in (0, 800, 400, 200, 100, 50):
            cfg = dict(scrub=period, wdt=300, ecc=True)
            write_out(f"sweep_{period}", pool.map(job, [("tmr", f, cfg, None) for f in fl], chunksize=64))
        print("sweep done", flush=True)
    with open(f"{OUT}/golden.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["addr", "data"])
        for a, d in gt: w.writerow([a, d])
    print("golden cycles", gcyc, "writes", len(gt))

if __name__ == "__main__":
    main()
