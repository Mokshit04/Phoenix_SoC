function g = phx_golden(C, imem)
%PHX_GOLDEN  Fault-free run of one core: the reference ("answer sheet") for every other run.
cfg = struct('scrub', 0, 'wdt', 0, 'ecc', 0);
r = phx_run(zeros(0, 5), cfg, 1, [], 40000, C, imem, []);
g.trace = r.bus.trace(1:r.bus.tn, :);
g.mem = r.bus.dmem(1:C.APP_WORDS);
g.cycles = r.cycles;
end
