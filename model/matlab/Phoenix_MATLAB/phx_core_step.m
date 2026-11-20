function c = phx_core_step(c, irq, iresp, dresp, C)
%PHX_CORE_STEP  Advance one core by one clock cycle.
%   iresp = [valid err op a b c]  instruction response delivered this cycle (valid = 0: none)
%   dresp = [valid data err]       data response delivered this cycle
s = c.state;
if s == C.F_REQ
    if irq ~= 0 && c.ie ~= 0                      % take the interrupt
        c.mepc = c.pc; c.ie = 0; c.pc = C.HANDLER;
    else
        c.state = C.F_WAIT;
    end
elseif s == C.F_WAIT
    if iresp(1) ~= 0
        if iresp(2) ~= 0
            c.state = C.TRAP;                     % bus error on fetch
        else
            c.ir = iresp(3:6); c.state = C.EX;
        end
    end
elseif s == C.EX && c.ir(1) == 0
    c.state = C.TRAP;                             % no instruction latched: illegal state
elseif s == C.EX
    op = c.ir(1); a = c.ir(2); b = c.ir(3); cc = c.ir(4);
    nxt = mod(c.pc + 4, C.M32);
    if op == C.OP_LD || op == C.OP_ST
        c.state = C.D_WAIT;
    else
        if op == C.OP_LI
            c.r(a + 1) = mod(b, C.M32);
        elseif op == C.OP_ADD
            c.r(a + 1) = mod(c.r(b + 1) + c.r(cc + 1), C.M32);
        elseif op == C.OP_ADDI
            c.r(a + 1) = mod(c.r(b + 1) + cc, C.M32);
        elseif op == C.OP_BNE
            if c.r(a + 1) ~= c.r(b + 1)
                nxt = cc;
            end
        elseif op == C.OP_JMP
            nxt = a;
        elseif op == C.OP_EI
            c.ie = 1;
        elseif op == C.OP_CSRR
            c.r(a + 1) = c.mepc;
        elseif op == C.OP_CSRW
            c.mepc = c.r(a + 1);
        elseif op == C.OP_MRET
            nxt = c.mepc; c.ie = 1;
        elseif op == C.OP_HALT
            c.state = C.HALT; nxt = c.pc;
        end
        c.r(1) = 0;
        if c.state == C.EX
            c.pc = nxt; c.state = C.F_REQ;
        end
    end
elseif s == C.D_WAIT && c.ir(1) == 0
    c.state = C.TRAP;
elseif s == C.D_WAIT
    if dresp(1) ~= 0
        if dresp(3) ~= 0
            c.state = C.TRAP;                     % bus error on load or store
        else
            if c.ir(1) == C.OP_LD
                c.r(c.ir(2) + 1) = mod(dresp(2), C.M32);
            end
            c.r(1) = 0;
            c.pc = mod(c.pc + 4, C.M32); c.state = C.F_REQ;
        end
    end
end
c = phx_core_apply_stuck(c);
end
