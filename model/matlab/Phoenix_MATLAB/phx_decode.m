function r = phx_decode(addr, C)
%PHX_DECODE  Address decoder: looks only at address bits [31:28].
nib = floor(addr / 268435456);         % addr / 2^28
if nib == 0
    r = C.R_IMEM;
elseif nib == 2
    r = C.R_DMEM;
elseif nib == 4
    r = C.R_PERIPH;
elseif nib == 5
    r = C.R_ACC;
elseif nib == 14
    r = C.R_RM;
else
    r = C.R_NONE;                       % unmapped: the default target answers with an error
end
end
