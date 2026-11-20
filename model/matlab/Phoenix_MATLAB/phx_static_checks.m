function S = phx_static_checks(C, n_voter, n_decode, n_words)
%PHX_STATIC_CHECKS  Direct checks of the voter, the decoder and the SECDED code.
widths = [1 32 1 1 4 32 32];                    % the 7 fields = 103 bits
% ---- voter and detector: one core wrong in 1..103 bits
S.voter_trials = n_voter; S.voter_masked = 0; S.voter_located = 0;
for t = 1:n_voter
    g = zeros(1, 7);
    for f = 1:7, g(f) = randi([0, 2^widths(f) - 1]); end
    v = {g, g, g}; k = randi(3);
    % flip 1..103 DIFFERENT bits of the chosen core (distinct positions, so two flips of the
    % same bit can never cancel and leave the core accidentally correct)
    for pos = randperm(103, randi(103))
        f = find(cumsum(widths) >= pos, 1); b = pos - sum(widths(1:f-1)) - 1;
        v{k}(f) = double(bitxor(uint64(v{k}(f)), uint64(2^b)));
    end
    y = phx_vote(v{1}, v{2}, v{3});
    fl = phx_detect(v{1}, v{2}, v{3}, y);
    S.voter_masked = S.voter_masked + isequal(y, g);
    S.voter_located = S.voter_located + isequal(fl, (1:3) == k);
end
% ---- decoder: every address maps to exactly one region or to the error target
S.decode_trials = n_decode; ok = true;
nib2reg = [C.R_IMEM 0 C.R_DMEM 0 C.R_PERIPH C.R_ACC 0 0 0 0 0 0 0 0 C.R_RM 0];
for t = 1:n_decode
    a = randi([0, 2^32 - 1]);
    ok = ok && (phx_decode(a, C) == nib2reg(floor(a / 2^28) + 1));
end
S.decode_ok = ok;
% ---- SECDED: every single-bit and every double-bit error on random words
S.ecc_single = 0; S.ecc_single_ok = 0; S.ecc_double = 0; S.ecc_double_ok = 0;
for w = 1:n_words
    d = randi([0, 2^32 - 1]); cw = uint64(phx_ecc_encode(d, C));
    for i = 0:38
        e1 = bitxor(cw, uint64(2^i));
        [dd, st] = phx_ecc_decode(double(e1), C);
        S.ecc_single = S.ecc_single + 1; S.ecc_single_ok = S.ecc_single_ok + (dd == d && st == 1);
        for j = i + 1:38
            [~, st2] = phx_ecc_decode(double(bitxor(e1, uint64(2^j))), C);
            S.ecc_double = S.ecc_double + 1; S.ecc_double_ok = S.ecc_double_ok + (st2 == 2);
        end
    end
end
end
