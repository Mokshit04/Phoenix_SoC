function v = phx_last(x, len)
%PHX_LAST  Last logged value of a To Workspace signal, as a 1 x len row vector.
%   Handles the shapes Simulink uses for logged data (T x len, or 1 x len x T).
if ndims(x) == 3
    x = x(:, :, end);
elseif size(x, 1) > 1 && size(x, 2) == len
    x = x(end, :);
end
v = reshape(x, 1, []);
v = v(end - len + 1:end);
end
