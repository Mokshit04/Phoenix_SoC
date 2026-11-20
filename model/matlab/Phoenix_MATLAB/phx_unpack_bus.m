function b = phx_unpack_bus(v, C)
%PHX_UNPACK_BUS  2063-value Simulink signal -> bus struct (inverse of phx_pack_bus).
v = reshape(v, 1, numel(v));        % Simulink may deliver the signal as a column
n = C.DMEM_WORDS; T = C.TRACE_MAX;
b.ecc = v(n + 2*T + 13);
b.dmem = v(1:n);
b.i_pend = v(n + 2*T + 1 : n + 2*T + 6);
b.d_pend = v(n + 2*T + 7 : n + 2*T + 9);
b.trace = reshape(v(n + 1 : n + 2*T), T, 2);
b.tn = v(n + 2*T + 10);
b.overflow = v(n + 2*T + 11);
b.restarted = v(n + 2*T + 12);
b.ecc_corrected = v(n + 2*T + 14);
b.ecc_uncorrectable = v(n + 2*T + 15);
end
