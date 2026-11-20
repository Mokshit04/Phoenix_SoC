function [res, T] = phx_run_trace(faults, cfg, n_cores, perm, max_cycles, C, imem, golden)
%PHX_RUN_TRACE  Same as phx_run, but also records what happens on every cycle (for the demo).
%   T has one entry per cycle:
%     T.cycle        cycle number
%     T.agree        n_cores x N: 1 = core output agrees with the vote, 0 = disagrees, NaN = in reset
%     T.state        n_cores x N: core control state (0 fetch .. 5 trap)
%     T.rm_state     PHX_RM state (0 monitor, 1 save, 2 reset, 3 restore, 4 verify, 5 safe)
%     T.irq          resynchronisation interrupt
%     T.reset        1 when the cores are held in reset
%     T.same         1 when the internal state (pc, registers, ...) of all cores is identical
%   The logic is identical to phx_run; only the recording is added.

has_rm = (n_cores == 3);
if has_rm, rm = phx_rm_new(cfg.scrub, cfg.wdt, C); else, rm = phx_rm_new(0, 0, C); end
bus = phx_bus_new(cfg.ecc, C);
cores = repmat(phx_core_reset(-1, C), 1, n_cores);
if ~isempty(perm), cores(perm(1) + 1) = phx_core_reset(perm(2), C); end
if ~isempty(faults)
    [~, order] = sort(faults(:, 1)); faults = faults(order, :);
end
nf = size(faults, 1); fi = 1;
V = zeros(n_cores, 7);
T.cycle = zeros(1, max_cycles); T.agree = nan(n_cores, max_cycles); T.state = nan(n_cores, max_cycles);
T.rm_state = zeros(1, max_cycles); T.irq = zeros(1, max_cycles); T.reset = zeros(1, max_cycles);
T.same = ones(1, max_cycles);
cyc = 0;

for cyc = 0:max_cycles - 1
    i = cyc + 1; T.cycle(i) = cyc;
    while fi <= nf && faults(fi, 1) == cyc
        f = faults(fi, :); fi = fi + 1;
        if f(2) == 1
            k = mod(f(3), n_cores) + 1;
            cores(k) = phx_core_flip(cores(k), f(4), f(5));
        else
            bus.dmem(f(3) + 1) = double(bitxor(uint64(bus.dmem(f(3) + 1)), uint64(2^f(5))));
        end
    end
    s1 = snap(cores(1));
    for k = 2:n_cores
        if ~isequal(snap(cores(k)), s1), T.same(i) = 0; end
    end
    irq = has_rm * rm.irq;
    for k = 1:n_cores
        V(k, :) = phx_core_out(cores(k), irq, C);
        T.state(k, i) = cores(k).state;
    end
    if has_rm
        voted = phx_vote(V(1, :), V(2, :), V(3, :));
        flags = phx_detect(V(1, :), V(2, :), V(3, :), voted);
    else
        voted = V(1, :); flags = [false false false];
    end
    T.agree(:, i) = ~flags(1:n_cores)';
    iresp = bus.i_pend; dresp = bus.d_pend;
    bus.i_pend = zeros(1, 6); bus.d_pend = zeros(1, 3);
    [bus, rmcmd] = phx_bus_request(bus, voted, rm.sp, has_rm, imem, C);
    if has_rm
        rm = phx_rm_tick(rm, flags, cyc, rmcmd, C);
        T.rm_state(i) = rm.state; T.irq(i) = rm.irq;
        if rm.system_reset || rm.core_reset
            T.reset(i) = 1;
            for k = 1:n_cores, cores(k) = phx_core_reset(cores(k).stuck, C); end
            bus = phx_bus_drop(bus, rm.system_reset, C);
            if ~rm.system_reset && rm.state == C.SAFE, break; end
            continue;
        end
    end
    for k = 1:n_cores
        cores(k) = phx_core_step(cores(k), irq, iresp, dresp, C);
    end
    if phx_should_stop(cores, rm, flags, has_rm, C), break; end
end

n = cyc + 1;
T.cycle = T.cycle(1:n); T.agree = T.agree(:, 1:n); T.state = T.state(:, 1:n);
T.rm_state = T.rm_state(1:n); T.irq = T.irq(1:n); T.reset = T.reset(1:n); T.same = T.same(1:n);
T.agree(:, T.reset == 1) = NaN;
res.cycles = n; res.bus = bus; res.rm = rm; res.cores = cores;
res.outcome = phx_classify(bus, rm, cores, has_rm, golden, C);
res.latency = -1; res.recovery = -1;
if has_rm && rm.t_detect >= 0 && nf > 0, res.latency = rm.t_detect - min(faults(:, 1)); end
if has_rm && rm.recoveries > 0, res.recovery = rm.t_recovered - rm.t_detect; end
end

function s = snap(c)
s = [c.pc c.mepc c.ie c.state c.r];
end
