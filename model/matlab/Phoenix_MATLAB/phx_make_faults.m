function F = phx_make_faults(kind, n, gcyc)
%PHX_MAKE_FAULTS  New random fault scenarios ("fresh" mode), same rules as the Python model.
%   Each F{i} is a K x 5 matrix [cycle type unit target bit].
%   Fault time: a random cycle from 20 to (reference length - 6).
F = cell(1, n);
for i = 1:n
    t = randi([20, gcyc - 6]);
    switch kind
        case 'core'                                   % one flip: random core, place, bit
            F{i} = [t 1 randi([0 2]) randi(11) randi([0 31])];
        case 'mem1'                                   % one flip in one of the 60 array words
            F{i} = [t 2 randi([0 59]) 0 randi([0 31])];
        case 'mem2'                                   % two different bits of the same word
            w = randi([0 59]); b = randperm(32, 2) - 1;
            F{i} = [t 2 w 0 b(1); t 2 w 0 b(2)];
        case 'dbl_near'                               % two different cores within 3 cycles
            c = randperm(3, 2) - 1;
            F{i} = [t 1 c(1) randi(11) randi([0 31]); t + randi([0 2]) 1 c(2) randi(11) randi([0 31])];
        case 'dbl_far'                                % two different cores at independent times
            c = randperm(3, 2) - 1;
            F{i} = [t 1 c(1) randi(11) randi([0 31]); randi([20, gcyc - 6]) 1 c(2) randi(11) randi([0 31])];
    end
end
end
