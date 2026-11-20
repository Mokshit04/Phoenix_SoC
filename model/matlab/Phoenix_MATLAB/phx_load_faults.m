function F = phx_load_faults(file, nruns)
%PHX_LOAD_FAULTS  Read a fault list exported from the Python model.
%   CSV columns: run, cycle, type, unit, target, bit   (header row first)
%   F{i} is the K x 5 matrix [cycle type unit target bit] for run i.
A = csvread(file, 1, 0);
if nargin < 2 || isempty(nruns)
    nruns = max(A(:, 1));
end
F = cell(1, nruns);
for i = 1:nruns
    F{i} = A(A(:, 1) == i, 2:6);
end
end
