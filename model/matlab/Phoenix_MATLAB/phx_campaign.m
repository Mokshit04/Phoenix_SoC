function out = phx_campaign(F, cfg, n_cores, perm, max_cycles, C, imem, golden, workers)
%PHX_CAMPAIGN  Run one configuration over a list of fault scenarios F (cell array).
%   workers > 0 spreads the runs over the parallel pool; 0 runs them one after another.
n = numel(F);
oc = zeros(1, n); la = -ones(1, n); re = -ones(1, n); cy = zeros(1, n);
parfor (i = 1:n, workers)
    r = phx_run(F{i}, cfg, n_cores, perm, max_cycles, C, imem, golden);
    oc(i) = r.outcome; la(i) = r.latency; re(i) = r.recovery; cy(i) = r.cycles;
end
out = struct('outcome', oc, 'latency', la, 'recovery', re, 'cycles', cy);
end
