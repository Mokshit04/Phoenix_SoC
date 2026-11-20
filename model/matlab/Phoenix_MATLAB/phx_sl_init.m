function [ca, cb, cc, bv, rmv] = phx_sl_init(cfg, perm, C)
%PHX_SL_INIT  Reset values of the five Simulink registers (Unit Delay initial conditions).
%   perm = [core bit] for a permanent fault, or [] for none.
s = [-1 -1 -1];
if ~isempty(perm), s(perm(1) + 1) = perm(2); end
ca = phx_pack_core(phx_core_reset(s(1), C));
cb = phx_pack_core(phx_core_reset(s(2), C));
cc = phx_pack_core(phx_core_reset(s(3), C));
bv = phx_pack_bus(phx_bus_new(cfg.ecc, C), C);
rmv = phx_pack_rm(phx_rm_new(cfg.scrub, cfg.wdt, C));
end
