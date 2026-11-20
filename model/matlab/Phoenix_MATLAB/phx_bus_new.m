function bus = phx_bus_new(ecc, C)
%PHX_BUS_NEW  PHX_BUS with its memories and peripherals, in the reset state.
%   ecc = 1 stores every data-memory word with SECDED check bits.
bus.ecc = ecc;
if ecc
    bus.dmem = repmat(phx_ecc_encode(0, C), 1, C.DMEM_WORDS);
else
    bus.dmem = zeros(1, C.DMEM_WORDS);
end
bus.i_pend = zeros(1, 6);         % instruction response waiting for next cycle [valid err op a b c]
bus.d_pend = zeros(1, 3);         % data response waiting for next cycle [valid data err]
bus.trace = zeros(C.TRACE_MAX, 2);% every application-visible write: [address data]
bus.tn = 0;                       % number of writes since start (or since the last system reset)
bus.overflow = 0;                 % 1 if more writes happened than the buffer holds
bus.restarted = 0;                % 1 after a system reset (the Python "RESTART" marker)
bus.ecc_corrected = 0;
bus.ecc_uncorrectable = 0;
end
