function s = phx_unpack_rm(v)
%PHX_UNPACK_RM  28-value Simulink signal -> recovery-manager struct (inverse of phx_pack_rm).
v = reshape(v, 1, numel(v));        % Simulink may deliver the signal as a column
s.N = v(1); s.M = v(2); s.t_save = v(3); s.t_restore = v(4); s.reset_cycles = v(5);
s.scrub_period = v(6); s.wdt_limit = v(7);
s.state = v(8); s.sp = v(9); s.irq = v(10); s.faulty = v(11); s.attempts = v(12); s.cnt = v(13);
s.sysreset_done = v(14);
s.detections = v(15); s.recoveries = v(16); s.sysresets = v(17); s.scrubs = v(18); s.wdt_fired = v(19);
s.t_detect = v(20); s.t_recovered = v(21);
s.core_reset = v(22); s.system_reset = v(23); s.ev_valid = v(24); s.ev_val = v(25);
s.scrub_cnt = v(26); s.wdt_cnt = v(27); s.is_scrub = v(28);
end
