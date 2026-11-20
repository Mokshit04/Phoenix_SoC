function build_phoenix_simulink()
%BUILD_PHOENIX_SIMULINK  Creates phoenix_soc_model.slx, the block version of the Phoenix model.
%
%   Run once:  >> build_phoenix_simulink
%
%   The model is drawn the way the hardware is built:
%     * five REGISTERS (Unit Delay blocks) hold all state: core A, core B, core C, PHX_BUS
%       with its memories, and PHX_RM. They update once per clock (Simulink step = 1 cycle).
%     * the LOGIC between them is MATLAB Function blocks: fault injector, three core output
%       blocks, voter, discrepancy detector, PHX_BUS, PHX_RM, three core next-state blocks,
%       bus reset control and the end-of-run check.
%   Every block calls the same phx_* functions as run_phoenix_campaign.m, so the block model
%   and the script cannot drift apart.

mdl  = 'phoenix_soc_model';
here = fileparts(mfilename('fullpath'));
addpath(here);
C = phx_const();

% ---- default values of the variables the model uses (run_phoenix_simulink overrides them)
cfg = struct('scrub', 400, 'wdt', 300, 'ecc', 1);
[ca, cb, cc, bv, rmv] = phx_sl_init(cfg, [], C);
assignin('base', 'phx_coreA0', ca);  assignin('base', 'phx_coreB0', cb);
assignin('base', 'phx_coreC0', cc);  assignin('base', 'phx_bus0', bv);
assignin('base', 'phx_rm0', rmv);    assignin('base', 'phx_faults', -ones(4, 5));

% ---- fresh model
if bdIsLoaded(mdl), close_system(mdl, 0); end
f = fullfile(here, [mdl '.slx']);
if exist(f, 'file'), delete(f); end
new_system(mdl);
open_system(mdl);
set_param(mdl, 'Solver', 'FixedStepDiscrete', 'FixedStep', '1', 'StartTime', '0', ...
          'StopTime', '39999', 'SaveTime', 'off', 'SaveOutput', 'off', ...
          'ReturnWorkspaceOutputs', 'on');
code = phx_sl_blocks();

% ---- registers (Unit Delay = one clock of delay = a bank of flip-flops)
reg(mdl, 'Reg Core A', 'phx_coreA0', [60  70 120 110]);
reg(mdl, 'Reg Core B', 'phx_coreB0', [60 170 120 210]);
reg(mdl, 'Reg Core C', 'phx_coreC0', [60 270 120 310]);
reg(mdl, 'Reg PHX_BUS', 'phx_bus0',  [60 400 120 440]);
reg(mdl, 'Reg PHX_RM', 'phx_rm0',    [60 560 120 600]);
add_block('simulink/Sources/Digital Clock', [mdl '/Cycle'], 'SampleTime', '1', ...
          'Position', [55 680 125 710]);

% ---- logic blocks
fcn(mdl, 'Fault Injector',   code.inject,    [200  60 330 450], 'orange');
fcn(mdl, 'Core A out',       code.core_out,  [420  60 530 110], 'lightBlue');
fcn(mdl, 'Core B out',       code.core_out,  [420 160 530 210], 'lightBlue');
fcn(mdl, 'Core C out',       code.core_out,  [420 260 530 310], 'lightBlue');
fcn(mdl, 'Voter',            code.voter,     [620 120 720 220], 'magenta');
fcn(mdl, 'Detector',         code.detector,  [620 270 720 380], 'magenta');
fcn(mdl, 'PHX_BUS',          code.bus,       [820 400 960 520], 'gray');
fcn(mdl, 'PHX_RM',           code.rm,        [820 570 960 670], 'magenta');
fcn(mdl, 'Core A next',      code.core_next, [1060  60 1180 130], 'lightBlue');
fcn(mdl, 'Core B next',      code.core_next, [1060 170 1180 240], 'lightBlue');
fcn(mdl, 'Core C next',      code.core_next, [1060 280 1180 350], 'lightBlue');
fcn(mdl, 'Bus Reset Control',code.bus_reset, [1060 420 1180 480], 'gray');
fcn(mdl, 'End Of Run',       code.stop,      [1280 120 1400 260], 'yellow');
add_block('simulink/Sinks/Stop Simulation', [mdl '/Stop'], 'Position', [1450 175 1490 205]);

% the injector's fault list is a parameter (from the workspace), not an input port
rt = sfroot;
ch = rt.find('-isa', 'Stateflow.EMChart', 'Path', [mdl '/Fault Injector']);
d = ch.find('-isa', 'Stateflow.Data', 'Name', 'phx_faults');
d.Scope = 'Parameter';

% ---- final values to the workspace (only the last cycle is kept)
logb(mdl, 'sl_coreA', [1280 320 1360 340]);
logb(mdl, 'sl_coreB', [1280 360 1360 380]);
logb(mdl, 'sl_coreC', [1280 400 1360 420]);
logb(mdl, 'sl_bus',   [1280 450 1360 470]);
logb(mdl, 'sl_rm',    [1280 600 1360 620]);
logb(mdl, 'sl_t',     [1280 690 1360 710]);

% ---- wiring: registers -> injector
w(mdl, 'Cycle/1', 'Fault Injector/1');
w(mdl, 'Reg Core A/1', 'Fault Injector/2'); w(mdl, 'Reg Core B/1', 'Fault Injector/3');
w(mdl, 'Reg Core C/1', 'Fault Injector/4'); w(mdl, 'Reg PHX_BUS/1', 'Fault Injector/5');
% injector -> core output logic (+ interrupt from PHX_RM register)
w(mdl, 'Fault Injector/1', 'Core A out/1'); w(mdl, 'Fault Injector/2', 'Core B out/1');
w(mdl, 'Fault Injector/3', 'Core C out/1');
w(mdl, 'Reg PHX_RM/1', 'Core A out/2'); w(mdl, 'Reg PHX_RM/1', 'Core B out/2'); w(mdl, 'Reg PHX_RM/1', 'Core C out/2');
% core outputs -> voter and detector
w(mdl, 'Core A out/1', 'Voter/1'); w(mdl, 'Core B out/1', 'Voter/2'); w(mdl, 'Core C out/1', 'Voter/3');
w(mdl, 'Core A out/1', 'Detector/1'); w(mdl, 'Core B out/1', 'Detector/2'); w(mdl, 'Core C out/1', 'Detector/3');
w(mdl, 'Voter/1', 'Detector/4');
% PHX_BUS: bus state (after memory faults), PHX_RM register, voted request
w(mdl, 'Fault Injector/4', 'PHX_BUS/1'); w(mdl, 'Reg PHX_RM/1', 'PHX_BUS/2'); w(mdl, 'Voter/1', 'PHX_BUS/3');
% PHX_RM: its register, detector flags, cycle number, register writes from the bus
w(mdl, 'Reg PHX_RM/1', 'PHX_RM/1'); w(mdl, 'Detector/1', 'PHX_RM/2');
w(mdl, 'Cycle/1', 'PHX_RM/3'); w(mdl, 'PHX_BUS/4', 'PHX_RM/4');
% core next-state logic
nm = {'A', 'B', 'C'};
for k = 1:3
    nb = ['Core ' nm{k} ' next'];
    w(mdl, sprintf('Fault Injector/%d', k), [nb '/1']);
    w(mdl, 'Reg PHX_RM/1', [nb '/2']); w(mdl, 'PHX_RM/1', [nb '/3']);
    w(mdl, 'PHX_BUS/2', [nb '/4']); w(mdl, 'PHX_BUS/3', [nb '/5']);
    w(mdl, [nb '/1'], ['Reg Core ' nm{k} '/1']);
    w(mdl, [nb '/1'], sprintf('End Of Run/%d', k));
    w(mdl, [nb '/1'], ['sl_core' nm{k} '/1']);
end
% bus reset control, registers, end-of-run check, logging
w(mdl, 'PHX_BUS/1', 'Bus Reset Control/1'); w(mdl, 'PHX_RM/1', 'Bus Reset Control/2');
w(mdl, 'Bus Reset Control/1', 'Reg PHX_BUS/1'); w(mdl, 'Bus Reset Control/1', 'sl_bus/1');
w(mdl, 'PHX_RM/1', 'Reg PHX_RM/1'); w(mdl, 'PHX_RM/1', 'sl_rm/1');
w(mdl, 'PHX_RM/1', 'End Of Run/4'); w(mdl, 'Detector/1', 'End Of Run/5');
w(mdl, 'End Of Run/1', 'Stop/1');
w(mdl, 'Cycle/1', 'sl_t/1');

% ---- title note
try
    note = Simulink.Annotation([mdl '/Phoenix SoC pre-RTL model: registers (left) hold all state; ' ...
        'logic blocks compute one clock cycle. One Simulink step = one clock cycle.']);
    note.Position = [200 20];
catch
end

save_system(mdl, f);
fprintf('Built and saved %s\n', f);
try
    set_param(mdl, 'SimulationCommand', 'update');      % compile check (takes a little while)
    fprintf('Model compiled without errors. Next: run run_phoenix_simulink.m\n');
catch err
    fprintf(2, 'Model built, but the compile check reported:\n%s\n', err.message);
end
end

% ---------------------------------------------------------------- helpers
function reg(mdl, name, ic, pos)
add_block('simulink/Discrete/Unit Delay', [mdl '/' name], 'InitialCondition', ic, ...
          'SampleTime', '1', 'Position', pos, 'BackgroundColor', 'green');
end

function fcn(mdl, name, txt, pos, colour)
add_block('simulink/User-Defined Functions/MATLAB Function', [mdl '/' name], 'Position', pos);
rt = sfroot;
ch = rt.find('-isa', 'Stateflow.EMChart', 'Path', [mdl '/' name]);
ch.Script = txt;
set_param([mdl '/' name], 'BackgroundColor', colour);
end

function logb(mdl, var, pos)
add_block('simulink/Sinks/To Workspace', [mdl '/' var], 'VariableName', var, ...
          'SaveFormat', 'Timeseries', 'MaxDataPoints', '1', 'Position', pos);
end

function w(mdl, from, to)
add_line(mdl, from, to, 'autorouting', 'on');
end
