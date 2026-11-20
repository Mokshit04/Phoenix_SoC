function v = phx_core_out(c, irq, C)
%PHX_CORE_OUT  Bus outputs of one core this cycle (combinational, from its state).
%   v = [instr_req instr_addr data_req data_we data_be data_addr data_wdata]
%   These 7 fields are the 103 bits that the voters compare (1+32+1+1+4+32+32).
v = zeros(1, 7);
if c.state == C.F_REQ && ~(irq ~= 0 && c.ie ~= 0)
    v(1) = 1; v(2) = c.pc;                               % instruction fetch
elseif c.state == C.EX && c.ir(1) ~= 0 && (c.ir(1) == C.OP_LD || c.ir(1) == C.OP_ST)
    addr = mod(c.r(c.ir(3) + 1) + c.ir(4), C.M32);
    v(3) = 1; v(5) = 15; v(6) = addr;                    % data access, all 4 bytes
    if c.ir(1) == C.OP_ST
        v(4) = 1; v(7) = c.r(c.ir(2) + 1);
    end
end
end
