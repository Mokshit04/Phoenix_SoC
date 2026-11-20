function c = phx_core_apply_stuck(c)
%PHX_CORE_APPLY_STUCK  Permanent fault: force one program-counter bit to 1.
if c.stuck > 0
    c.pc = double(bitor(uint64(c.pc), uint64(2^c.stuck)));
end
end
