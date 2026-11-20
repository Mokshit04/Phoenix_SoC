function C = phx_const()
%PHX_CONST  Constants of the Phoenix pre-RTL model (addresses, codes, settings).
%   Same values as phoenix_model_v2.py. Every other phx_* function takes C as input.

% Note for Simulink: code generation does not allow a structure to be read while it is still
% being built, so every value below is written as a number, never as C.something + offset.

% ---- address map (hex value in the comment)
C.M32       = 4294967296;          % 2^32, used to wrap 32-bit arithmetic
C.IMEM_BASE = 0;                   % 0x0000_0000
C.DMEM_BASE = 536870912;           % 0x2000_0000
C.PERI_BASE = 1073741824;          % 0x4000_0000
C.ACC_BASE  = 1342177280;          % 0x5000_0000
C.RM_BASE   = 3758096384;          % 0xE000_0000
C.GPIO_ODR  = 1073741824;          % 0x4000_0000  example peripheral slots used by the test program
C.UART_TX   = 1073754112;          % 0x4000_3000
C.RM_SP     = 3758096384;          % 0xE000_0000  PHX_RM "saved stack pointer" register
C.RM_WDT    = 3758096388;          % 0xE000_0004  PHX_RM watchdog register
C.DMEM_WORDS = 1024;
C.SAVE_AREA = 536874752;           % 0x2000_0F00: where the processor state is saved
C.RESULT    = 536872960;           % 0x2000_0800
C.APP_WORDS = 960;                 % words below SAVE_AREA (compared with the reference)
C.N_ITER    = 60;                  % loop count of the test program
C.HANDLER   = 384;                 % 0x180: resynchronisation interrupt handler

% ---- region codes returned by phx_decode
C.R_NONE = 0; C.R_IMEM = 1; C.R_DMEM = 2; C.R_PERIPH = 3; C.R_ACC = 4; C.R_RM = 5;

% ---- core states (same numbers as the Python model)
C.F_REQ = 0; C.F_WAIT = 1; C.EX = 2; C.D_WAIT = 3; C.HALT = 4; C.TRAP = 5;

% ---- instruction opcodes of the small test core
C.OP_LI = 1; C.OP_LD = 2; C.OP_ST = 3; C.OP_ADD = 4; C.OP_ADDI = 5; C.OP_BNE = 6;
C.OP_JMP = 7; C.OP_EI = 8; C.OP_CSRR = 9; C.OP_CSRW = 10; C.OP_MRET = 11; C.OP_HALT = 12;

% ---- fault targets inside a core: 1 pc, 2..8 r1..r7, 9 mepc, 10 ie, 11 state
C.N_TARGETS = 11;

% ---- recovery-manager states
C.MONITOR = 0; C.SAVE = 1; C.RESET = 2; C.RESTORE = 3; C.VERIFY = 4; C.SAFE = 5;

% ---- outcome codes (same order as the Python ORDER list)
C.O_REC = 1; C.O_ECC = 2; C.O_NOEFF = 3; C.O_RST = 4; C.O_SAFE = 5;
C.O_DUE = 6; C.O_LAT = 7; C.O_WRONG = 8; C.O_HANG = 9; C.O_CRASH = 10;

% ---- SECDED (39,32): the 32 code-word positions that hold data (1..38, not powers of two)
dp = zeros(1, 32); k = 0;
for p = 1:38
    if bitand(uint64(p), uint64(p - 1)) ~= 0
        k = k + 1; dp(k) = p;
    end
end
C.DATA_POS = dp;

% ---- trace buffer size (the reference program makes 123 writes)
C.TRACE_MAX = 512;
end
