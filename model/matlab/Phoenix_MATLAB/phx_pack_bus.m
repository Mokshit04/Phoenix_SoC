function v = phx_pack_bus(s, C)
%PHX_PACK_BUS  Bus struct -> 2063-value row vector (a Simulink signal). Inverse: phx_unpack_bus.
v = [s.dmem reshape(s.trace, 1, 2 * C.TRACE_MAX) s.i_pend s.d_pend ...
     s.tn s.overflow s.restarted s.ecc s.ecc_corrected s.ecc_uncorrectable];
end
