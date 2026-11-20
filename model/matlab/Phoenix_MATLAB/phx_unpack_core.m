function c = phx_unpack_core(v)
%PHX_UNPACK_CORE  17-value Simulink signal -> core struct (inverse of phx_pack_core).
v = reshape(v, 1, numel(v));        % Simulink may deliver the signal as a column
c.pc = v(1); c.mepc = v(2); c.ie = v(3); c.state = v(4);
c.r = v(5:12); c.ir = v(13:16); c.stuck = v(17);
end
