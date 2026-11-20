function [vals, fixed, bad] = phx_mem_values(bus, C)
%PHX_MEM_VALUES  Application memory as software would read it (ECC applied when enabled).
%   vals: 1 x 960 values (NaN where ECC reports an uncorrectable word)
n = C.APP_WORDS;
fixed = 0; bad = 0;
if ~bus.ecc
    vals = bus.dmem(1:n);
    return;
end
vals = zeros(1, n);
for i = 1:n
    [d, st] = phx_ecc_decode(bus.dmem(i), C);
    if st == 2
        vals(i) = NaN; bad = bad + 1;
    else
        vals(i) = d; fixed = fixed + (st == 1);
    end
end
end
