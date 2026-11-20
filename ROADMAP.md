# Phoenix SoC roadmap

Status as of 20 November 2026. The architecture is frozen for RTL (ADR revision of 19 November 2026).
**No RTL exists yet.** "Verified (model)" means checked in the pre-RTL model only.

## Done

| Item | Status | Reference |
|---|---|---|
| Architecture decisions ADR-001 to ADR-020 | Decided | `docs/adr/` |
| Pre-RTL model and fault campaign (68,400 runs) | Verified (model) | `model/python/` |
| MATLAB re-implementation: 5,640 / 5,640 runs identical to Python | Verified (model) | `model/matlab/` |
| Simulink block model: 52 / 52 cases identical to the MATLAB script | Verified (model) | `model/matlab/` |
| Static checks: voter, address decoder, SECDED | Verified (model) | `model/` |
| Pre-RTL verification report | Done | `docs/reports/` |
| Engineering Bible, Edition 3 | Done | `docs/` |

## Next: specifications

1. **PHX_BUS v1.0 specification**: signal list, cycle timing, wait states (including ECC read-modify-write for byte stores), error response, timeout register.
2. Integration specification: peripheral base addresses, reset sequencing, interrupt line numbers.
3. Memory wrapper and SECDED specification.
4. Register specifications: GPIO, Timer, PWM, UART.
5. PHX_CORE specification: Ibex parameters, voter and detector, treatment of every Ibex output.
6. PHX_RM specification: state machine, registers, scrub and watchdog, counters, fault injection, resync software routine.

## Build order (one shared RTL for both tracks)

| Step | Content | Status |
|---|---|---|
| 1 | Single-core SoC in simulation: Ibex, PHX_BUS, IMEM/DMEM, GPIO, Timer, PWM, UART | Planned |
| 2 | FPGA bring-up (Track A) and first SAED32 synthesis (Track B) of step 1 | Planned |
| 3 | Bus timeout and PHX_RM, peripheral-fault path | Planned |
| 4 | Three cores, voters, detector, PHX_RM core-fault path, scrub, watchdog, SECDED; repeat the model campaign on the RTL | Planned |
| 5 | Application, profiling and the PHX_ACC accelerator | Planned (application not yet chosen) |
| 6 | Track A: fault campaign on the FPGA board and results paper. Track B: hierarchical place and route, timing, gate-level simulation in SAED32 | Planned |

Fabrication is deferred.

## Open decisions

- Application and workload (blocks PHX_ACC only)
- IMEM and DMEM sizes (parameters until the SAED32 SRAM macros are known)
- FPGA board (Artix-7 100T class preferred)
- Scan insertion in the SAED32 flow
