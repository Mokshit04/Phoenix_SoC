function res = phx_sl_result(ca, cb, cc, bv, rmv, t_end, faults, C, golden)
%PHX_SL_RESULT  Turn the final register values of a Simulink run into the same result
%   struct that phx_run returns (outcome, latency, recovery time, cycles).
cores = [phx_unpack_core(ca), phx_unpack_core(cb), phx_unpack_core(cc)];
bus = phx_unpack_bus(bv, C);
rm = phx_unpack_rm(rmv);
res.cycles = t_end + 1;
res.outcome = phx_classify(bus, rm, cores, true, golden, C);
res.latency = -1; res.recovery = -1;
if rm.t_detect >= 0 && ~isempty(faults)
    res.latency = rm.t_detect - min(faults(:, 1));
end
if rm.recoveries > 0 && rm.t_recovered >= 0 && rm.t_detect >= 0
    res.recovery = rm.t_recovered - rm.t_detect;
end
res.bus = bus; res.rm = rm; res.cores = cores;
end
