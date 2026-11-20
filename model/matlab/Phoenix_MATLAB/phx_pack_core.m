function v = phx_pack_core(s)
%PHX_PACK_CORE  Core struct -> 17-value row vector (a Simulink signal). Inverse: phx_unpack_core.
v = [s.pc s.mepc s.ie s.state s.r s.ir s.stuck];
end
