function bus = phx_bus_drop(bus, restart, C)
%PHX_BUS_DROP  Cores are being reset: cancel any response still in flight.
%   restart = 1 for a system reset: the write record starts again from empty,
%   because the program restarts from the beginning.
bus.i_pend = zeros(1, 6); bus.d_pend = zeros(1, 3);
if restart
    bus.restarted = 1; bus.tn = 0; bus.overflow = 0;
    bus.trace = zeros(C.TRACE_MAX, 2);
end
end
