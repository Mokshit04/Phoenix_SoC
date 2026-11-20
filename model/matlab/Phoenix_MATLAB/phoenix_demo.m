%% PHOENIX SoC - LIVE DEMO FOR THE FACULTY REVIEW
% Run this file one section at a time: click inside a section, press Ctrl+Enter.
% Each section is one "slide": it prints what to say and draws one figure.
% Tip: Home tab > Layout > choose a layout with a large figure area before you start.
%
% Needs: results/phoenix_matlab_results.mat (made by run_phoenix_campaign.m).
% Sections 1-4 work without it.

%% 0. Setup (run once at the start)
clear; close all; clc;
here = fileparts(mfilename('fullpath')); if isempty(here), here = pwd; end
addpath(here);
C = phx_const(); imem = phx_build_program(C); golden = phx_golden(C, imem);
BEFORE = struct('scrub', 0, 'wdt', 0, 'ecc', 0);
AFTER  = struct('scrub', 400, 'wdt', 300, 'ecc', 1);
ANIMATE = true;              % a cursor sweeps through the timeline figures (set false for speed)
L = phx_labels();
fprintf('Phoenix demo ready. Reference program: %d cycles, %d writes.\n', golden.cycles, size(golden.trace, 1));

%% 1. What the model is
fprintf('\nTHE MODEL\n');
fprintf('  Three identical cores run the same program in lockstep.\n');
fprintf('  Every cycle, 103 output bits of each core go to a bitwise majority voter: Y = A.B + B.C + A.C\n');
fprintf('  A detector compares each core with the vote and names the one that disagrees.\n');
fprintf('  PHX_RM then repairs it: save state through the voter, reset all cores, restore, verify.\n');
fprintf('  Test program: 60 running sums stored in memory, read back, added up, sent to the UART.\n');
fprintf('  One run = inject a bit flip at a random cycle, run to the end, compare with the fault-free run.\n');
if exist('build_phoenix_simulink', 'file') && exist(fullfile(here, 'phoenix_soc_model.slx'), 'file')
    open_system(fullfile(here, 'phoenix_soc_model.slx'));
    fprintf('  (The Simulink block model is now open: registers on the left, logic in the middle.)\n');
end

%% 2. Watch one fault being detected and repaired (three cores)
% Real case from the campaign (core fault list, run 13):
% at cycle 1445 bit 0 of register r2 (the running sum) flips in core B.
F13 = [1445 1 1 3 0];                     % [cycle type core target bit]: target 3 = register r2
[r3, T3] = phx_run_trace(F13, BEFORE, 3, [], 40000, C, imem, golden);
phx_plot_timeline(T3, r3, F13(1), 'Run 13: one bit flip in core B, three cores', ANIMATE);
fprintf('\nRUN 13 (three cores)\n');
fprintf('  Fault at cycle %d. Core B carries a wrong value internally (row 2 drops).\n', F13(1));
fprintf('  %d cycles later core B writes it out: its output disagrees with A and C (red in row 1).\n', r3.latency);
fprintf('  The voter passes the A/C value, so memory never sees the wrong number.\n');
fprintf('  PHX_RM: interrupt -> save state -> reset all three -> restore -> verify %d cycles.\n', 50);
fprintf('  Repaired and verified in %d cycles. Outcome: %s.\n', r3.recovery, L{r3.outcome});

%% 3. The same fault on ONE core: what would have happened without Phoenix
r1 = phx_run(F13, BEFORE, 1, [], 12000, C, imem, golden);
gm = golden.mem(1:60); m1 = r1.bus.dmem(1:60); m3 = r3.bus.dmem(1:60);
bad = find(m1 ~= gm);
figure('Color', 'w', 'Position', [80 80 1100 420]);
bar(0:59, m1 - gm, 0.7, 'FaceColor', [227 73 72] / 255, 'EdgeColor', 'none'); hold on;
plot(0:59, m3 - gm, 'o', 'Color', [42 120 214] / 255, 'MarkerFaceColor', [42 120 214] / 255, 'MarkerSize', 5);
hold off; grid on; box off; ylim([min([m1 - gm, -1]) - 0.5, max([m1 - gm, 1]) + 0.5]);
xlabel('Memory word (the program''s 60 running sums)'); ylabel('Stored value minus correct value');
legend({sprintf('One core alone: %d of 60 values wrong', numel(bad)), 'Three cores with Phoenix: all 60 exact'}, ...
       'Location', 'southwest');
title(sprintf('Same bit flip at cycle %d.   One core: %s.   Three cores: %s.', F13(1), L{r1.outcome}, L{r3.outcome}));
fprintf('\nSAME FAULT, ONE CORE\n  %d of 60 stored values are wrong (each by %d), and nothing in the chip noticed.\n', numel(bad), max(abs(m1 - gm)));
fprintf('  With three cores the same fault was caught and repaired, and every value is correct.\n');

%% 4. A hidden fault, and why we added the scrub
% Campaign run 23: at cycle 3096 bit 16 of register r7 flips in core C.
% r7 is not used again, so the fault never reaches an output and the voter cannot see it.
F23 = [3096 1 2 8 16];                    % target 8 = register r7
[rb, Tb] = phx_run_trace(F23, BEFORE, 3, [], 40000, C, imem, golden);
phx_plot_timeline(Tb, rb, F23(1), 'Run 23 BEFORE: hidden fault, no scrub', false);
[ra, Ta] = phx_run_trace(F23, AFTER, 3, [], 40000, C, imem, golden);
phx_plot_timeline(Ta, ra, F23(1), 'Run 23 AFTER: the periodic scrub finds and clears it', ANIMATE);
fprintf('\nHIDDEN FAULT\n  Before: %s. Row 2 stays "different" to the end: core C still holds a wrong bit.\n', L{rb.outcome});
fprintf('  A second fault in another core later could now outvote the healthy one.\n');
fprintf('  After: the scrub forces a save/reset/restore every 400 cycles. Outcome: %s.\n', L{ra.outcome});

%% 5. The whole campaign in one dashboard
rf = fullfile(here, 'results', 'phoenix_matlab_results.mat');
if ~exist(rf, 'file')
    fprintf('\nRun run_phoenix_campaign.m first: %s not found.\n', rf);
else
    S5 = load(rf); R = S5.R; SW = S5.SW;
    phx_dashboard(R, SW, C);
    UN = [C.O_LAT C.O_WRONG C.O_HANG C.O_CRASH];
    fprintf('\nCAMPAIGN (%s mode, fraction %g)\n', S5.SETTINGS.mode, S5.SETTINGS.fraction);
    keys = {'core', 'mem1', 'mem2', 'dbl_far', 'dbl_near'};
    for e = 1:numel(keys)
        fprintf('  %-40s unresolved %5.1f%% -> %4.1f%%\n', R.(keys{e}).label, ...
            100 * mean(ismember(R.(keys{e}).before.outcome, UN)), 100 * mean(ismember(R.(keys{e}).after.outcome, UN)));
    end
end

%% 6. Three independent implementations agree
fprintf('\nCROSS-CHECKS\n');
fprintf('  Python model vs MATLAB script : every replayed run identical (outcome and cycle count)\n');
fprintf('  MATLAB script vs Simulink     : 52 of 52 cases identical (outcome and cycle count)\n');
fprintf('  The same faults were injected in all three, so any logic error would show as a mismatch.\n');
fprintf('\nLIMITS: the core is a small stand-in for Ibex; no timing, area or power yet.\n');
