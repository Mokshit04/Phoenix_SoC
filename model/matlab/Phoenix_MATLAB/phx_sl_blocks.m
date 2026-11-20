function code = phx_sl_blocks()
%PHX_SL_BLOCKS  Source code placed inside each MATLAB Function block of the Simulink model.
%   Every block is pure logic: its state lives in the Unit Delay registers around it.
%   The blocks call the same phx_* functions as the script, so both share one model.
%   Returned as a struct: field name = block, value = code text.

code.inject = strjoin({
'function [ca, cb, cc, bv] = inject(t, ca0, cb0, cc0, bv0, phx_faults)'
'% Fault injector: applies every row of phx_faults whose cycle equals t.'
'% phx_faults is a block parameter (4 x 5): [cycle type unit target bit]; unused rows have cycle = -1.'
'C = phx_const();'
'ca = reshape(ca0, 1, numel(ca0)); cb = reshape(cb0, 1, numel(cb0));   % rows, whatever shape arrives'
'cc = reshape(cc0, 1, numel(cc0)); bv = reshape(bv0, 1, numel(bv0));'
'for k = 1:size(phx_faults, 1)'
'    if phx_faults(k, 1) == t'
'        if phx_faults(k, 2) == 1'
'            u = mod(phx_faults(k, 3), 3);'
'            if u == 0'
'                ca = phx_pack_core(phx_core_flip(phx_unpack_core(ca), phx_faults(k, 4), phx_faults(k, 5)));'
'            elseif u == 1'
'                cb = phx_pack_core(phx_core_flip(phx_unpack_core(cb), phx_faults(k, 4), phx_faults(k, 5)));'
'            else'
'                cc = phx_pack_core(phx_core_flip(phx_unpack_core(cc), phx_faults(k, 4), phx_faults(k, 5)));'
'            end'
'        else'
'            w = phx_faults(k, 3) + 1;'
'            bv(w) = double(bitxor(uint64(bv(w)), uint64(2^phx_faults(k, 5))));'
'        end'
'    end'
'end'}, newline);

code.core_out = strjoin({
'function y = core_out(cv, rmv)'
'% Output logic of one Ibex-stand-in core: its bus request this cycle.'
'C = phx_const();'
'rm = phx_unpack_rm(rmv);'
'y = phx_core_out(phx_unpack_core(cv), rm.irq, C);'}, newline);

code.voter = strjoin({
'function y = voter(a, b, c)'
'% Bitwise 2-of-3 majority on the 103 bus-output bits: Y = A.B + B.C + A.C'
'y = phx_vote(reshape(a, 1, 7), reshape(b, 1, 7), reshape(c, 1, 7));'}, newline);

code.detector = strjoin({
'function flags = detector(a, b, c, voted)'
'% One flag per core: 1 if that core disagrees with the voted value.'
'flags = double(phx_detect(reshape(a, 1, 7), reshape(b, 1, 7), reshape(c, 1, 7), reshape(voted, 1, 7)));'}, newline);

code.bus = strjoin({
'function [bv_mid, iresp, dresp, rmcmd] = bus(bv, rmv, voted)'
'% PHX_BUS v1.0 with IMEM, DMEM (+ECC), peripherals and the PHX_RM registers.'
'% Delivers last cycle''s responses and accepts this cycle''s voted request.'
'persistent imem'
'C = phx_const();'
'if isempty(imem)'
'    imem = phx_build_program(C);'
'end'
'b = phx_unpack_bus(bv, C);'
'rm = phx_unpack_rm(rmv);'
'iresp = b.i_pend; dresp = b.d_pend;'
'b.i_pend = zeros(1, 6); b.d_pend = zeros(1, 3);'
'[b, rmcmd] = phx_bus_request(b, reshape(voted, 1, 7), rm.sp, true, imem, C);'
'bv_mid = phx_pack_bus(b, C);'}, newline);

code.rm = strjoin({
'function rmv_next = rm(rmv, flags, t, rmcmd)'
'% PHX_RM recovery manager: one tick of its state machine.'
'C = phx_const();'
'rmv_next = phx_pack_rm(phx_rm_tick(phx_unpack_rm(rmv), reshape(flags, 1, 3), t, reshape(rmcmd, 1, 3), C));'}, newline);

code.core_next = strjoin({
'function cv_next = core_next(cv, rmv, rmv_next, iresp, dresp)'
'% Next-state logic of one core: reset if PHX_RM says so, otherwise step.'
'C = phx_const();'
'c = phx_unpack_core(cv);'
'rm = phx_unpack_rm(rmv); rn = phx_unpack_rm(rmv_next);'
'if rn.system_reset ~= 0 || rn.core_reset ~= 0'
'    c = phx_core_reset(c.stuck, C);'
'else'
'    c = phx_core_step(c, rm.irq, reshape(iresp, 1, 6), reshape(dresp, 1, 3), C);'
'end'
'cv_next = phx_pack_core(c);'}, newline);

code.bus_reset = strjoin({
'function bv_next = bus_reset(bv_mid, rmv_next)'
'% Cancels responses in flight when the cores are reset.'
'C = phx_const();'
'rn = phx_unpack_rm(rmv_next);'
'b = phx_unpack_bus(bv_mid, C);'
'if rn.system_reset ~= 0'
'    b = phx_bus_drop(b, 1, C);'
'elseif rn.core_reset ~= 0'
'    b = phx_bus_drop(b, 0, C);'
'end'
'bv_next = phx_pack_bus(b, C);'}, newline);

code.stop = strjoin({
'function stop = stop_check(ca, cb, cc, rmv_next, flags)'
'% 1 when the run is over (program finished, or the safe state was entered).'
'C = phx_const();'
'rn = phx_unpack_rm(rmv_next);'
'cores = [phx_unpack_core(ca), phx_unpack_core(cb), phx_unpack_core(cc)];'
'if rn.system_reset ~= 0'
'    stop = 0;'
'elseif rn.core_reset ~= 0'
'    stop = double(rn.state == C.SAFE);'
'else'
'    stop = double(phx_should_stop(cores, rn, reshape(flags, 1, 3) ~= 0, true, C));'
'end'}, newline);
end
