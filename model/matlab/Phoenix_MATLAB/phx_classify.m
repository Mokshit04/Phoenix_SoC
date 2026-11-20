function code = phx_classify(bus, rm, cores, has_rm, golden, C)
%PHX_CLASSIFY  Mark one run against the fault-free reference ("answer sheet").
%   golden.trace : every write of the reference run [address data]
%   golden.mem   : reference contents of the 960 application words
[vals, fixed_at_end, bad] = phx_mem_values(bus, C);
mem_ok = isequal(vals, golden.mem);                  % NaN never equals anything
ng = size(golden.trace, 1);
tr_ok = ~bus.overflow && bus.tn == ng && isequal(bus.trace(1:bus.tn, :), golden.trace);
n = numel(cores);
halted = zeros(1, n);
for k = 1:n
    halted(k) = (cores(k).state == C.HALT);
end

if ~has_rm                                           % single unprotected core
    if cores(1).state == C.TRAP, code = C.O_CRASH; return; end
    if ~halted(1),               code = C.O_HANG;  return; end
    if mem_ok && tr_ok, code = C.O_NOEFF; else, code = C.O_WRONG; end
    return;
end
if rm.state == C.SAFE,  code = C.O_SAFE; return; end
if sum(halted) < 2,     code = C.O_HANG; return; end
if bus.restarted                                     % compare what happened after the system reset
    if mem_ok && tr_ok, code = C.O_RST; else, code = C.O_WRONG; end
    return;
end
if tr_ok && bad > 0 && all(isnan(vals) | vals == golden.mem)
    code = C.O_DUE; return;                          % ECC flagged a word; no wrong value was used
end
if ~(mem_ok && tr_ok), code = C.O_WRONG; return; end
if rm.recoveries > 0,  code = C.O_REC; return; end
if bus.ecc_corrected > 0 || fixed_at_end > 0, code = C.O_ECC; return; end
s1 = core_snap(cores(1));
for k = 2:n
    if ~isequal(core_snap(cores(k)), s1)
        code = C.O_LAT; return;                      % a wrong bit is still hidden in a core
    end
end
code = C.O_NOEFF;
end

function s = core_snap(c)
s = [c.pc c.mepc c.ie c.state c.r];
end
