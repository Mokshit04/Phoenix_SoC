function c = phx_core_flip(c, target, bit)
%PHX_CORE_FLIP  Inject one bit flip into a core.
%   target: 1 pc, 2..8 registers r1..r7, 9 mepc, 10 interrupt enable, 11 control state
m = uint64(2^bit);
if target == 1
    c.pc = double(bitxor(uint64(c.pc), m));
elseif target >= 2 && target <= 8
    c.r(target) = double(bitxor(uint64(c.r(target)), m));     % r(target) is register r(target-1)
elseif target == 9
    c.mepc = double(bitxor(uint64(c.mepc), m));
elseif target == 10
    c.ie = double(bitxor(uint64(c.ie), uint64(1)));
elseif target == 11
    c.state = mod(double(bitxor(uint64(c.state), uint64(2^mod(bit, 2)))), 4);
end
end
