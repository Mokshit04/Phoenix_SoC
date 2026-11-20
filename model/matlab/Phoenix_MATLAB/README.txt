PHOENIX SoC - PRE-RTL MODEL IN MATLAB AND SIMULINK
===================================================

This folder is the MATLAB version of phoenix_model_v2.py. It contains two things:

  1. THE SCRIPT      run_phoenix_campaign.m   (same model as the Python file, same output)
  2. THE BLOCKS      build_phoenix_simulink.m (builds phoenix_soc_model.slx)
                     run_phoenix_simulink.m   (runs example cases on the block model)

Both use the same phx_*.m functions, so the script and the block model are one model.

The data folder holds the exact faults the Python run injected (seed 2026) and the Python
outcome of every run. In "replay" mode MATLAB injects the same faults, so its results can be
compared with Python run by run.


WHAT YOU NEED
-------------
  - MATLAB (R2020b or newer recommended)
  - Simulink (only for the block model)
  - Parallel Computing Toolbox (optional; makes the full campaign several times faster)


STEP 1 - OPEN THE FOLDER
------------------------
  1. Unzip Phoenix_MATLAB.zip somewhere simple, e.g. D:\Phoenix_MATLAB
  2. Start MATLAB.
  3. In the "Current Folder" panel on the left, go into the Phoenix_MATLAB folder
     (or type in the Command Window:  cd D:\Phoenix_MATLAB  and press Enter).
     You should see files such as run_phoenix_campaign.m in the panel.


STEP 2 - RUN THE SCRIPT (quick check first)
-------------------------------------------
  1. Double-click run_phoenix_campaign.m to open it in the Editor.
  2. Near the top you will see the SETTINGS block. Leave it as it is for the first run:
        SETTINGS.mode     = 'replay';
        SETTINGS.fraction = 0.1;      % a tenth of the runs: a quick check
  3. Press the green "Run" button in the Editor toolbar (or press F5).
  4. Watch the Command Window. You should see, in order:
        - Reference run: 3124 cycles, 123 writes ...  identical to the Python reference: yes
        - STATIC CHECKS (voter, decoder, SECDED)
        - one progress line per experiment
        - RESULTS: the outcome percentages
        - COMPARISON WITH THE PYTHON MODEL: share of runs identical to Python (expect 100%)
  5. Figures and a .mat file are saved in the new "results" folder.

  For the full campaign (same numbers as the report): set SETTINGS.fraction = 1.0 and run
  again. This is 68,400 runs. The script prints the time each experiment takes, so after the
  first lines you can judge how long the rest will take. With the Parallel Computing Toolbox
  it uses all CPU cores (the first start of the parallel pool takes about 30 seconds).

  'fresh' mode: SETTINGS.mode = 'fresh' makes new random faults with MATLAB's own random
  generator. The percentages will be close to Python's but not identical, as with any new
  random sample.


STEP 3 - BUILD THE SIMULINK MODEL (once)
----------------------------------------
  1. In the Command Window type:   build_phoenix_simulink   and press Enter.
  2. It creates and opens phoenix_soc_model.slx. Layout, left to right:
        green  = registers (Unit Delay): Core A, Core B, Core C, PHX_BUS, PHX_RM
        orange = Fault Injector
        blue   = core logic (output logic and next-state logic of each core)
        pink   = Voter, Detector, PHX_RM
        grey   = PHX_BUS (memories, decoder, peripherals) and Bus Reset Control
        yellow = End Of Run check, which stops the simulation
     One Simulink step = one clock cycle.
  3. At the end it compiles the model. "Model compiled without errors" means it is ready.
     Double-click any block to see its code.


STEP 4 - RUN THE SIMULINK MODEL
-------------------------------
  1. Open run_phoenix_simulink.m and press Run (F5).
  2. It runs 52 example cases (fault-free, 5 from each fault class before and after, one
     permanent fault) on the Simulink model AND on the script, and prints both outcomes
     side by side with "yes" when they agree.
  3. To run more cases, raise RUNS_PER_CLASS at the top of the file.


IF SOMETHING GOES WRONG
-----------------------
  "Undefined function phx_..."   MATLAB is not in the Phoenix_MATLAB folder. Do Step 1.3.
  Parallel pool will not start   Set SETTINGS.parallel = false. Everything still works, slower.
  Simulink compile error         Copy the full red message. The usual cause is an older MATLAB
                                 release; R2020b or newer is recommended.
  Run is slow                    Lower SETTINGS.fraction (0.05 is a quick test).


FILE LIST
---------
  run_phoenix_campaign.m     main script
  build_phoenix_simulink.m   builds the Simulink model
  run_phoenix_simulink.m     runs cases on the Simulink model and compares with the script
  phx_const.m                addresses, codes and settings
  phx_build_program.m        the test program the cores run
  phx_core_*.m               the small test core (reset, outputs, one step, bit flip)
  phx_vote.m, phx_detect.m   majority voter and discrepancy detector
  phx_decode.m               address decoder
  phx_bus_*.m                PHX_BUS, memories and peripherals
  phx_ecc_*.m                SECDED (39,32) memory error code
  phx_rm_*.m                 recovery manager PHX_RM
  phx_run.m                  one complete run, cycle by cycle
  phx_classify.m             marks a run against the reference
  phx_sl_*.m, phx_pack_*.m,
  phx_unpack_*.m             Simulink block code and signal packing
  data/                      fault lists and Python outcomes for replay
  tests/phx_test_blocks.m    checks the Simulink block code without Simulink
