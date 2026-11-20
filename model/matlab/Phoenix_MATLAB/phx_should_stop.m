function stop = phx_should_stop(cores, rm, flags, has_rm, C)
%PHX_SHOULD_STOP  End-of-run test, evaluated after the cores have stepped.
n = numel(cores);
nh = 0; nt = 0;
for k = 1:n
    nh = nh + (cores(k).state == C.HALT);
    nt = nt + (cores(k).state == C.TRAP);
end
stop = false;
if ~has_rm
    stop = (cores(1).state == C.HALT || cores(1).state == C.TRAP);
    return;
end
idle = (rm.state == C.MONITOR) || (rm.state == C.SAVE && rm.cnt <= 1 && rm.is_scrub);
if idle && nh >= 2 && ~any(flags)
    stop = true;                       % two or more cores finished and they agree
elseif rm.wdt_limit == 0 && rm.state == C.MONITOR && nt >= 2
    stop = true;                       % crashed and nothing (no watchdog) will ever restart it
end
end
