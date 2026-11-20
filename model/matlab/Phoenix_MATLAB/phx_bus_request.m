function [bus, rmcmd] = phx_bus_request(bus, voted, rm_sp, has_rm, imem, C)
%PHX_BUS_REQUEST  PHX_BUS handles the voted request of this cycle.
%   Protocol of the model: the request is granted in the same cycle and the response
%   (read data + error flag) is delivered one cycle later (bus.i_pend / bus.d_pend).
%   rm_sp  current value of the PHX_RM saved-stack-pointer register (read data for RM_SP).
%   rmcmd  [sp_write sp_value wdt_kick]: register writes for PHX_RM, applied before its tick.
rmcmd = [0 0 0];
ireq = voted(1); iaddr = voted(2); dreq = voted(3); dwe = voted(4);
daddr = voted(6); dwdata = voted(7);

% ---- I-channel: point to point to IMEM
if ireq ~= 0
    idx = floor(iaddr / 4);
    if phx_decode(iaddr, C) == C.R_IMEM && mod(iaddr, 4) == 0 && idx < size(imem, 1)
        bus.i_pend = [1 0 imem(idx + 1, :)];
    else
        bus.i_pend = [1 1 0 0 0 0];                       % error response
    end
end

% ---- D-channel: address decoder selects the target
if dreq ~= 0
    tgt = phx_decode(daddr, C);
    if tgt == C.R_DMEM
        idx = floor((daddr - C.DMEM_BASE) / 4);
        if idx >= C.DMEM_WORDS
            bus.d_pend = [1 0 1];
        elseif dwe ~= 0
            if bus.ecc
                bus.dmem(idx + 1) = phx_ecc_encode(dwdata, C);
            else
                bus.dmem(idx + 1) = dwdata;
            end
            if daddr < C.SAVE_AREA
                bus = add_trace(bus, daddr, dwdata, C);
            end
            bus.d_pend = [1 0 0];
        elseif bus.ecc
            [d, st] = phx_ecc_decode(bus.dmem(idx + 1), C);
            if st == 2
                bus.ecc_uncorrectable = bus.ecc_uncorrectable + 1;
                bus.d_pend = [1 0 1];                     % two bad bits: error response
            else
                if st == 1
                    bus.ecc_corrected = bus.ecc_corrected + 1;
                    bus.dmem(idx + 1) = phx_ecc_encode(d, C);   % write the corrected word back
                end
                bus.d_pend = [1 d 0];
            end
        else
            bus.d_pend = [1 bus.dmem(idx + 1) 0];
        end
    elseif tgt == C.R_PERIPH
        if dwe ~= 0
            bus = add_trace(bus, daddr, dwdata, C);
        end
        bus.d_pend = [1 0 0];
    elseif tgt == C.R_ACC
        bus.d_pend = [1 0 0];
    elseif tgt == C.R_RM
        if ~has_rm
            bus.d_pend = [1 0 0];                         % single-core build: register reads 0
        else
            sp = rm_sp;
            if dwe ~= 0
                if daddr == C.RM_SP
                    rmcmd(1) = 1; rmcmd(2) = dwdata; sp = dwdata;
                elseif daddr == C.RM_WDT
                    rmcmd(3) = 1;
                end
            end
            if daddr == C.RM_SP
                bus.d_pend = [1 sp 0];
            else
                bus.d_pend = [1 0 0];
            end
        end
    else
        bus.d_pend = [1 0 1];                             % default target: error response
    end
end
end

function bus = add_trace(bus, addr, data, C)
if bus.tn < C.TRACE_MAX
    bus.trace(bus.tn + 1, :) = [addr data];
else
    bus.overflow = 1;
end
bus.tn = bus.tn + 1;
end
