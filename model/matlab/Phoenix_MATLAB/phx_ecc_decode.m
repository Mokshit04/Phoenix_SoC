function [d, status] = phx_ecc_decode(cw, C)
%PHX_ECC_DECODE  Decode a 39-bit SECDED word.
%   status: 0 clean, 1 one bit corrected, 2 uncorrectable (two bits wrong)
w = uint64(cw);
syn = 0; ones_ = double(bitget(w, 1));
for p = 1:38
    if bitget(w, p + 1)
        syn = double(bitxor(uint64(syn), uint64(p))); ones_ = ones_ + 1;
    end
end
status = 0; d = 0;
if mod(ones_, 2) == 1                         % odd number of wrong bits: assume exactly one
    if syn > 38
        status = 2; return;
    end
    w = bitxor(w, uint64(2^syn));             % syn = 0 means the parity bit itself
    status = 1;
elseif syn ~= 0
    status = 2; return;                       % even weight, non-zero syndrome: two wrong bits
end
D = uint64(0);
for i = 1:32
    if bitget(w, C.DATA_POS(i) + 1)
        D = bitset(D, i);
    end
end
d = double(D);
end
