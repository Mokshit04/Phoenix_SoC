function rm = phx_rm_tick(rm, flags, cycle, rmcmd, C)
%PHX_RM_TICK  One clock cycle of the recovery manager.
%   flags  1x3 detector flags of this cycle;  rmcmd [sp_write sp_value wdt_kick] from the bus.
%   Sets rm.irq, rm.core_reset and rm.system_reset for the cores.

% ---- register writes from the bus (they happen before the tick, as in Python)
if rmcmd(1) ~= 0
    rm.sp = rmcmd(2); rm.ev_valid = 1; rm.ev_val = rmcmd(2);
end
if rmcmd(3) ~= 0
    rm.wdt_cnt = 0;
end

rm.core_reset = 0; rm.system_reset = 0;
ev_valid = rm.ev_valid; ev_val = rm.ev_val;
rm.ev_valid = 0;
n = sum(flags ~= 0);
first = first_flag(flags);

if rm.state == C.SAFE
    rm.core_reset = 1;
    return;
end

if rm.state == C.MONITOR
    rm.scrub_cnt = rm.scrub_cnt + 1; rm.wdt_cnt = rm.wdt_cnt + 1;
    if n == 1                                             % one core disagrees: start recovery
        rm = found(rm, first, cycle);
        rm.attempts = 0; rm.is_scrub = 0;
        rm.state = C.SAVE; rm.cnt = 0; rm.irq = 1;
    elseif n >= 2                                         % no majority: escalate at once
        rm.detections = rm.detections + 1;
        if rm.t_detect < 0
            rm.t_detect = cycle;
        end
        rm = escalate(rm, C);
    elseif rm.wdt_limit > 0 && rm.wdt_cnt > rm.wdt_limit  % watchdog expired
        rm.wdt_fired = rm.wdt_fired + 1;
        rm = escalate(rm, C);
    elseif rm.scrub_period > 0 && rm.scrub_cnt >= rm.scrub_period   % periodic resynchronisation
        rm.faulty = -1; rm.attempts = 0; rm.is_scrub = 1;
        rm.scrubs = rm.scrubs + 1;
        rm.state = C.SAVE; rm.cnt = 0; rm.irq = 1;
    end
elseif rm.state == C.SAVE
    rm.cnt = rm.cnt + 1;
    if rm.faulty < 0 && n == 1
        rm = found(rm, first, cycle);                     % a scrub exposed a hidden fault
    end
    others = 0;
    for k = 0:2
        if k ~= rm.faulty && flags(k + 1) ~= 0
            others = 1;
        end
    end
    if others
        rm = fail(rm, C);
    elseif ev_valid && ev_val ~= 0                        % software wrote "state saved"
        rm.irq = 0; rm.state = C.RESET; rm.cnt = rm.reset_cycles;
    elseif rm.cnt > rm.t_save
        rm = fail(rm, C);
    end
elseif rm.state == C.RESET
    rm.core_reset = 1; rm.cnt = rm.cnt - 1;
    if rm.cnt == 0
        rm.state = C.RESTORE; rm.cnt = 0;
    end
elseif rm.state == C.RESTORE
    rm.cnt = rm.cnt + 1;
    if n > 0
        rm = fail(rm, C);
    elseif ev_valid && ev_val == 0                        % software cleared it: "restore done"
        rm.state = C.VERIFY; rm.cnt = rm.N;
    elseif rm.cnt > rm.t_restore
        rm = fail(rm, C);
    end
elseif rm.state == C.VERIFY
    if n > 0
        rm = fail(rm, C);
    else
        rm.cnt = rm.cnt - 1;
        if rm.cnt == 0
            if rm.faulty >= 0
                rm.recoveries = rm.recoveries + 1; rm.t_recovered = cycle;
            end
            rm.state = C.MONITOR; rm.faulty = -1;
            rm.scrub_cnt = 0; rm.wdt_cnt = 0;
        end
    end
end
end

% ---------------------------------------------------------------- local functions
function k = first_flag(flags)
k = -1;
for i = 1:3
    if flags(i) ~= 0
        k = i - 1; return;
    end
end
end

function rm = found(rm, idx, cycle)
rm.faulty = idx; rm.detections = rm.detections + 1;
if rm.t_detect < 0
    rm.t_detect = cycle;
end
end

function rm = fail(rm, C)
rm.attempts = rm.attempts + 1;
if rm.attempts >= rm.M
    rm = escalate(rm, C);
elseif rm.sp ~= 0                       % state already saved: just reset and reload
    rm.state = C.RESET; rm.cnt = rm.reset_cycles; rm.irq = 0;
else
    rm.state = C.SAVE; rm.cnt = 0; rm.irq = 1;
end
end

function rm = escalate(rm, C)
rm.irq = 0;
if rm.sysreset_done
    rm.state = C.SAFE;                  % fault came back after a system reset: stop
else
    rm.sysreset_done = 1; rm.system_reset = 1;
    rm.sysresets = rm.sysresets + 1;
    rm.state = C.MONITOR; rm.sp = 0; rm.attempts = 0; rm.faulty = -1;
    rm.scrub_cnt = 0; rm.wdt_cnt = 0;
end
end
