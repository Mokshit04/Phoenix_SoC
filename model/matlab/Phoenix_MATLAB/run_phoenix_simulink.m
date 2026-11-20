%% PHOENIX SoC - SIMULINK BLOCK MODEL: run scenarios and compare with the script
% HOW TO RUN: run build_phoenix_simulink once, then open this file and press "Run" (F5).
%
% Each scenario runs the Simulink model (phoenix_soc_model.slx) and the MATLAB script model
% (phx_run) on exactly the same faults, and prints both outcomes side by side.
% Simulink is slower than the script, so it runs a set of example cases, not all 68,400.

clear; clc;
RUNS_PER_CLASS = 5;          % examples taken from each fault class of the Python campaign

here = fileparts(mfilename('fullpath'));
if isempty(here), here = pwd; end
addpath(here);
mdl = 'phoenix_soc_model';
if ~exist(fullfile(here, [mdl '.slx']), 'file')
    build_phoenix_simulink;
end
load_system(fullfile(here, [mdl '.slx']));
C = phx_const(); imem = phx_build_program(C); golden = phx_golden(C, imem);
L = phx_labels();
BEFORE = struct('scrub', 0, 'wdt', 0, 'ecc', 0);
AFTER  = struct('scrub', 400, 'wdt', 300, 'ecc', 1);
dataDir = fullfile(here, 'data');

% ---- scenarios: {name, faults (K x 5), configuration, permanent fault}
SC = {'Fault-free, after mechanisms', zeros(0, 5), AFTER, []};
classes = {'core', 'One flip in a core'; 'mem1', 'One flip in memory'; 'mem2', 'Two flips in one memory word';
           'dbl_far', 'Two cores, separate times'; 'dbl_near', 'Two cores, within 3 cycles'};
for e = 1:size(classes, 1)
    F = phx_load_faults(fullfile(dataDir, ['faults_' classes{e, 1} '.csv']), RUNS_PER_CLASS);
    for i = 1:RUNS_PER_CLASS
        SC(end + 1, :) = {sprintf('%s #%d, before', classes{e, 2}, i), F{i}, BEFORE, []}; %#ok<SAGROW>
        SC(end + 1, :) = {sprintf('%s #%d, after',  classes{e, 2}, i), F{i}, AFTER,  []}; %#ok<SAGROW>
    end
end
SC(end + 1, :) = {'Permanent fault (core B, pc bit 9), after', zeros(0, 5), AFTER, [1 9]};

% ---- run every scenario in Simulink and in the script
fprintf('%-44s %-36s %-36s %s\n', 'Scenario', 'Simulink', 'Script', 'Same');
same = 0;
for s = 1:size(SC, 1)
    faults = SC{s, 2}; cfg = SC{s, 3}; perm = SC{s, 4};
    fz = -ones(4, 5); fz(1:size(faults, 1), :) = faults;
    [ca, cb, cc, bv, rmv] = phx_sl_init(cfg, perm, C);
    in = Simulink.SimulationInput(mdl);
    in = in.setVariable('phx_faults', fz);
    in = in.setVariable('phx_coreA0', ca); in = in.setVariable('phx_coreB0', cb);
    in = in.setVariable('phx_coreC0', cc); in = in.setVariable('phx_bus0', bv);
    in = in.setVariable('phx_rm0', rmv);
    out = sim(in);
    t_end = phx_last(out.get('sl_t').Data, 1);
    rs = phx_sl_result(phx_last(out.get('sl_coreA').Data, 17), phx_last(out.get('sl_coreB').Data, 17), ...
                       phx_last(out.get('sl_coreC').Data, 17), phx_last(out.get('sl_bus').Data, numel(bv)), ...
                       phx_last(out.get('sl_rm').Data, 28), t_end, faults, C, golden);
    rr = phx_run(faults, cfg, 3, perm, 40000, C, imem, golden);
    ok = rs.outcome == rr.outcome && rs.cycles == rr.cycles;
    same = same + ok;
    fprintf('%-44s %-36s %-36s %s\n', SC{s, 1}, sprintf('%s (%d cyc)', L{rs.outcome}, rs.cycles), ...
            sprintf('%s (%d cyc)', L{rr.outcome}, rr.cycles), phx_yesno(ok));
end
fprintf('\n%d of %d scenarios give the same outcome and cycle count in Simulink and in the script.\n', same, size(SC, 1));
open_system(mdl);
