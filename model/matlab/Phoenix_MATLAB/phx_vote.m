function y = phx_vote(a, b, c)
%PHX_VOTE  Bitwise 2-of-3 majority on every field: Y = A.B + B.C + A.C
%   a, b, c are 1x7 bus-output vectors from cores A, B, C (103 bits in total).
A = uint64(a); B = uint64(b); Cc = uint64(c);
y = double(bitor(bitor(bitand(A, B), bitand(B, Cc)), bitand(A, Cc)));
end
