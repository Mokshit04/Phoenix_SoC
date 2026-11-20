# Phoenix pre-RTL model (Python)

A cycle-level executable model of the Phoenix SoC architecture, used to check the logic of the
recovery design before any RTL exists. It contains three small stand-in cores (not Ibex), the
103-bit majority voters, the discrepancy detector, PHX_BUS v1.0 (I-channel and D-channel), the
memories with optional SECDED, and the PHX_RM recovery manager with periodic scrub and watchdog.

| File | Purpose |
|---|---|
| `phoenix_model_v2.py` | The model and the full fault-injection campaign (before / after the protections) |
| `phoenix_model.py` | First version of the model (baseline architecture only), kept for history |
| `make_charts.py` | Draws the report figures from `results_v2.json` |
| `export_for_matlab.py` | Exports the exact fault lists and Python outcomes so the MATLAB port can replay them |
| `results_v2.json` | Results of the published campaign (68,400 runs, seed 2026) |

## Run

Requires Python 3.8+ (standard library only); `make_charts.py` also needs matplotlib.

```bash
python3 phoenix_model_v2.py --scale 0.05 --out quick_check.json   # quick check, about a minute
python3 phoenix_model_v2.py --scale 0.5    # the published campaign (68,400 runs, seed 2026)
python3 make_charts.py                      # figures from results_v2.json
```

The random seed is fixed (`--seed 2026`), so every run repeats exactly.

## What the model is not

It does not contain Ibex, gates, voltages or real timing. Cycle counts apply to the stand-in core
only. The results show that the recovery logic is sound; they do not predict Ibex, FPGA or ASIC
numbers. See `docs/reports/Phoenix_PreRTL_Verification_Report.pdf` for the full method and limits.
