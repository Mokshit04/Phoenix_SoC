function c = phx_core_reset(stuck, C)
%PHX_CORE_RESET  State of one core straight after reset.
%   stuck = bit number of a permanent program-counter fault, or -1 for none.
c.pc = 0; c.mepc = 0; c.ie = 0; c.state = C.F_REQ;
c.r = zeros(1, 8);            % r(1) is register r0 (always 0), r(k+1) is register rk
c.ir = zeros(1, 4);           % latched instruction [op a b c]; op = 0 means "none"
c.stuck = stuck;
c = phx_core_apply_stuck(c);
end
