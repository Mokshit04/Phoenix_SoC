function phx_test_blocks(nruns)
%PHX_TEST_BLOCKS  Checks the Simulink block code WITHOUT Simulink.
%   Writes the code of every MATLAB Function block to temporary files, then calls them in the
%   order Simulink executes them (registers -> injector -> core outputs -> voter -> detector ->
%   bus -> PHX_RM -> next-state logic -> registers), and compares every run with phx_run.
if nargin < 1, nruns = 20; end
here = fileparts(fileparts(mfilename('fullpath')));
addpath(here);
tmp = fullfile(tempdir, 'phx_block_test'); if ~exist(tmp, 'dir'), mkdir(tmp); end
code = phx_sl_blocks(); names = fieldnames(code);
for i = 1:numel(names)
    txt = code.(names{i});
    fn = regexp(txt, '=\s*(\w+)\(', 'tokens', 'once');
    fid = fopen(fullfile(tmp, [fn{1} '.m']), 'w'); fprintf(fid, '%s\n', txt); fclose(fid);
end
addpath(tmp); clear bus
C = phx_const(); imem = phx_build_program(C); g = phx_golden(C, imem);
B = struct('scrub', 0, 'wdt', 0, 'ecc', 0); A = struct('scrub', 400, 'wdt', 300, 'ecc', 1);
F = phx_load_faults(fullfile(here, 'data', 'faults_core.csv'), nruns);
M = phx_load_faults(fullfile(here, 'data', 'faults_mem2.csv'), nruns);
cases = {};
for i = 1:nruns
    cases(end+1, :) = {F{i}, B, []}; cases(end+1, :) = {F{i}, A, []}; cases(end+1, :) = {M{i}, A, []};
end
cases(end+1, :) = {zeros(0, 5), A, [1 9]};          % permanent fault
same = 0;
for k = 1:size(cases, 1)
    r1 = phx_run(cases{k, 1}, cases{k, 2}, 3, cases{k, 3}, 40000, C, imem, g);
    r2 = emulate(cases{k, 1}, cases{k, 2}, cases{k, 3}, 40000, C, g);
    ok = r1.outcome == r2.outcome && r1.cycles == r2.cycles && r1.latency == r2.latency;
    same = same + ok;
    if ~ok, fprintf('  case %d differs: run %d/%d, blocks %d/%d\n', k, r1.outcome, r1.cycles, r2.outcome, r2.cycles); end
end
fprintf('Simulink block code vs phx_run: %d of %d cases identical (outcome, cycles, latency)\n', same, size(cases, 1));
end

function res = emulate(faults, cfg, perm, max_cycles, C, g)
fz = -ones(4, 5); fz(1:size(faults, 1), :) = faults;  % same padding as the Simulink parameter
[ca, cb, cc, bv, rmv] = phx_sl_init(cfg, perm, C);
for t = 0:max_cycles - 1
    % registers are passed as COLUMNS here, the strictest case Simulink can produce
    [a, b, c, bvf] = inject(t, ca(:), cb(:), cc(:), bv(:), fz);
    ya = core_out(a(:), rmv(:)); yb = core_out(b(:), rmv(:)); yc = core_out(c(:), rmv(:));
    v = voter(ya(:), yb(:), yc(:)); fl = detector(ya(:), yb(:), yc(:), v(:));
    [bvm, ir, dr, cmd] = bus(bvf(:), rmv(:), v(:));
    rmn = rm(rmv(:), fl(:), t, cmd(:));
    an = core_next(a(:), rmv(:), rmn(:), ir(:), dr(:)); bn = core_next(b(:), rmv(:), rmn(:), ir(:), dr(:)); cn = core_next(c(:), rmv(:), rmn(:), ir(:), dr(:));
    bvn = bus_reset(bvm(:), rmn(:));
    st = stop_check(an(:), bn(:), cn(:), rmn(:), fl(:));
    assert(isrow(an) && isrow(bvn) && isrow(rmn) && isrow(ya) && isrow(v), 'a block output is not a row');
    ca = an; cb = bn; cc = cn; bv = bvn; rmv = rmn;     % clock edge: registers take the new values
    if st, break; end
end
res = phx_sl_result(ca, cb, cc, bv, rmv, t, faults, C, g);
end
