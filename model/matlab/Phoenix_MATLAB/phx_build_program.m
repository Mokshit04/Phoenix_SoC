function imem = phx_build_program(C)
%PHX_BUILD_PROGRAM  The test program, one instruction per row: [opcode a b c].
%   Row k holds the instruction at address 4*(k-1). Same program as build_program() in Python:
%   boot code at 0x000, application at 0x040, restore routine at 0x100, handler at 0x180.
%   Operand meaning:  li rd,imm | ld rd,rbase,off | st rsrc,rbase,off | add rd,ra,rb
%                     addi rd,ra,imm | bne ra,rb,target | jmp target | csrr rd | csrw rs

APP = 64; RESTORE = 256; HANDLER = C.HANDLER;
N = 108;                                     % 0x000 .. 0x1AC
imem = repmat([C.OP_HALT 0 0 0], N, 1);      % unused words are HALT, as in Python

% ---- boot: resume if PHX_RM holds a saved stack pointer, otherwise start the application
imem = put(imem, 0, [C.OP_LI 1 C.RM_SP 0; C.OP_LD 2 1 0; C.OP_BNE 2 0 RESTORE; C.OP_JMP APP 0 0]);

% ---- application
a = [C.OP_EI 0 0 0;
     C.OP_LI 1 0 0; C.OP_LI 2 0 0; C.OP_LI 3 C.N_ITER 0; C.OP_LI 4 C.DMEM_BASE 0;
     C.OP_LI 5 0 0; C.OP_LI 7 C.GPIO_ODR 0;
     % loop 1 at APP+28: running sum, store, read back, GPIO write, kick the watchdog
     C.OP_ADDI 1 1 1; C.OP_ADD 2 2 1; C.OP_ST 2 4 0; C.OP_LD 6 4 0; C.OP_ADD 5 5 6;
     C.OP_ST 1 7 0; C.OP_ST 0 0 C.RM_WDT; C.OP_ADDI 4 4 4; C.OP_BNE 1 3 APP+28;
     % second pass: read the 60 stored values back and add them up
     C.OP_LI 4 C.DMEM_BASE 0; C.OP_LI 1 0 0; C.OP_LI 5 0 0;
     % loop 2 at APP+76
     C.OP_LD 6 4 0; C.OP_ADD 5 5 6; C.OP_ST 0 0 C.RM_WDT; C.OP_ADDI 4 4 4; C.OP_ADDI 1 1 1;
     C.OP_BNE 1 3 APP+76;
     % results to memory and to the UART, then stop
     C.OP_LI 4 C.RESULT 0; C.OP_ST 2 4 0; C.OP_ST 5 4 4; C.OP_LI 6 C.UART_TX 0; C.OP_ST 5 6 0;
     C.OP_HALT 0 0 0];
imem = put(imem, APP, a);

% ---- resynchronisation handler: save r1..r7 and mepc, tell PHX_RM, then wait
h = zeros(12, 4);
for r = 1:7
    h(r, :) = [C.OP_ST r 0 C.SAVE_AREA + 4*r];
end
h(8, :)  = [C.OP_CSRR 1 0 0];
h(9, :)  = [C.OP_ST 1 0 C.SAVE_AREA + 32];
h(10, :) = [C.OP_LI 1 C.SAVE_AREA 0];
h(11, :) = [C.OP_ST 1 0 C.RM_SP];
h(12, :) = [C.OP_JMP HANDLER + 44 0 0];      % jump to itself until PHX_RM resets the cores
imem = put(imem, HANDLER, h);

% ---- restore routine (r2 holds the saved pointer, set by the boot code)
s = zeros(11, 4);
s(1, :) = [C.OP_LD 1 2 32];
s(2, :) = [C.OP_CSRW 1 0 0];
for k = 3:7
    s(k, :) = [C.OP_LD k 2 4*k];
end
s(8, :)  = [C.OP_ST 0 0 C.RM_SP];             % clear the saved pointer: "restore done"
s(9, :)  = [C.OP_LD 1 2 4];
s(10, :) = [C.OP_LD 2 2 8];
s(11, :) = [C.OP_MRET 0 0 0];
imem = put(imem, RESTORE, s);
end

function imem = put(imem, addr, rows)
first = addr / 4 + 1;
imem(first:first + size(rows, 1) - 1, :) = rows;
end
