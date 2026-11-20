function cw = phx_ecc_encode(d, C)
%PHX_ECC_ENCODE  SECDED (39,32) extended Hamming code.
%   Code-word positions 1..38 hold 32 data bits and 6 check bits (at 1,2,4,8,16,32).
%   Bit 0 is an overall parity bit that makes the whole word even.
w = uint64(0); D = uint64(d);
for i = 1:32
    if bitget(D, i)
        w = bitset(w, C.DATA_POS(i) + 1);
    end
end
for k = 0:5                                   % check bit k covers positions with bit k set
    par = 0;
    for p = 1:38
        if bitget(uint64(p), k + 1) && bitget(w, p + 1)
            par = 1 - par;
        end
    end
    if par
        w = bitset(w, 2^k + 1);
    end
end
ones_ = 0;
for p = 0:38
    ones_ = ones_ + double(bitget(w, p + 1));
end
if mod(ones_, 2) == 1
    w = bitset(w, 1);                         % overall parity bit
end
cw = double(w);
end
