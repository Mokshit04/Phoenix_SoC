function flags = phx_detect(a, b, c, voted)
%PHX_DETECT  Discrepancy detector: one flag per core, true if that core differs from the vote.
flags = [any(a ~= voted), any(b ~= voted), any(c ~= voted)];
end
