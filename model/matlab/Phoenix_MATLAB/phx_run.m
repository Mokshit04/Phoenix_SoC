function res = phx_run(faults, cfg, n_cores, perm, max_cycles, C, imem, golden)
%PHX_RUN  Simulate one run of the Phoenix model, cycle by cycle.
%   faults     K x 5 matrix, one row per injected fault: [cycle type unit target bit]
%              type 1 = core fault (unit = core 0..2, target 1..11, bit 0..31)
%              type 2 = memory fault (unit = data-memory word, bit 0..31)
%   cfg        struct with fields scrub, wdt, ecc (see phx_config)
%   n_cores    3 (protected cluster) or 1 (single unprotected core)
%   perm       [core bit] for a permanent program-counter fault, or [] for none
%   golden     reference result from the fault-free run, or [] while computing it
%   res        struct: outcome code, latency, recovery time, cycles, final bus/rm/cores

has_rm = (n_cores == 3);
if has_rm
    rm = phx_rm_new(cfg.scrub, cfg.wdt, C);
else
    rm = phx_rm_new(0, 0, C);                            % unused in the single-core build
end
bus = phx_bus_new(cfg.ecc, C);
cores = repmat(phx_core_reset(-1, C), 1, n_cores);
if ~isempty(perm)
    cores(perm(1) + 1) = phx_core_reset(perm(2), C);
end
if ~isempty(faults)
    [~, order] = sort(faults(:, 1));
    faults = faults(order, :);
end
nf = size(faults, 1); fi = 1;
V = zeros(n_cores, 7);
cyc = 0;

for cyc = 0:max_cycles - 1
    % ---- 1. inject the faults scheduled for this cycle
    while fi <= nf && faults(fi, 1) == cyc
        f = faults(fi, :); fi = fi + 1;
        if f(2) == 1
            k = mod(f(3), n_cores) + 1;
            cores(k) = phx_core_flip(cores(k), f(4), f(5));
        else
            bus.dmem(f(3) + 1) = double(bitxor(uint64(bus.dmem(f(3) + 1)), uint64(2^f(5))));
        end
    end
    % ---- 2. core outputs, voters, detector
    irq = has_rm * rm.irq;
    for k = 1:n_cores
        V(k, :) = phx_core_out(cores(k), irq, C);
    end
    if has_rm
        voted = phx_vote(V(1, :), V(2, :), V(3, :));
        flags = phx_detect(V(1, :), V(2, :), V(3, :), voted);
    else
        voted = V(1, :); flags = [false false false];
    end
    % ---- 3. bus: deliver last cycle's responses, accept this cycle's request
    iresp = bus.i_pend; dresp = bus.d_pend;
    bus.i_pend = zeros(1, 6); bus.d_pend = zeros(1, 3);
    [bus, rmcmd] = phx_bus_request(bus, voted, rm.sp, has_rm, imem, C);
    % ---- 4. recovery manager
    if has_rm
        rm = phx_rm_tick(rm, flags, cyc, rmcmd, C);
        if rm.system_reset
            for k = 1:n_cores, cores(k) = phx_core_reset(cores(k).stuck, C); end
            bus = phx_bus_drop(bus, 1, C);
            continue;
        end
        if rm.core_reset
            for k = 1:n_cores, cores(k) = phx_core_reset(cores(k).stuck, C); end
            bus = phx_bus_drop(bus, 0, C);
            if rm.state == C.SAFE, break; end
            continue;
        end
    end
    % ---- 5. cores advance one cycle
    for k = 1:n_cores
        cores(k) = phx_core_step(cores(k), irq, iresp, dresp, C);
    end
    % ---- 6. stop when the program has finished
    if phx_should_stop(cores, rm, flags, has_rm, C), break; end
end

res.cycles = cyc + 1;
res.bus = bus; res.rm = rm; res.cores = cores;
res.outcome = 0; res.latency = -1; res.recovery = -1;
if ~isempty(golden)
    res.outcome = phx_classify(bus, rm, cores, has_rm, golden, C);
    if has_rm && rm.t_detect >= 0 && nf > 0
        res.latency = rm.t_detect - min(faults(:, 1));
    end
    if has_rm && rm.recoveries > 0 && rm.t_recovered >= 0 && rm.t_detect >= 0
        res.recovery = rm.t_recovered - rm.t_detect;
    end
end
end
