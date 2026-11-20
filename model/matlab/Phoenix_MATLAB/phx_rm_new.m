function rm = phx_rm_new(scrub, wdt, C)
%PHX_RM_NEW  Recovery manager PHX_RM in its reset state.
%   scrub = periodic-resynchronisation period in cycles (0 = off)
%   wdt   = watchdog limit in cycles (0 = off)
rm.N = 50;              % verify window after a recovery
rm.M = 3;               % recovery attempts before escalation
rm.t_save = 400;        % timeout for the save step
rm.t_restore = 400;     % timeout for the restore step
rm.reset_cycles = 3;    % how long the cores are held in reset
rm.scrub_period = scrub;
rm.wdt_limit = wdt;
rm.state = C.MONITOR;
rm.sp = 0;              % saved stack pointer register
rm.irq = 0;             % resynchronisation interrupt to the cores
rm.faulty = -1;         % core being repaired: 0, 1, 2, or -1 for none
rm.attempts = 0; rm.cnt = 0;
rm.sysreset_done = 0;   % fault history: survives a system reset
rm.detections = 0; rm.recoveries = 0; rm.sysresets = 0; rm.scrubs = 0; rm.wdt_fired = 0;
rm.t_detect = -1; rm.t_recovered = -1;
rm.core_reset = 0; rm.system_reset = 0;
rm.ev_valid = 0; rm.ev_val = 0;   % "saved stack pointer written" event of this cycle
rm.scrub_cnt = 0; rm.wdt_cnt = 0;
rm.is_scrub = 0;
end
