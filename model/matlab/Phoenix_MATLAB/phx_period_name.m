function s = phx_period_name(p)
%PHX_PERIOD_NAME  Scrub period for printing ('off' for 0).
if p == 0, s = 'off'; else, s = sprintf('%d', p); end
end
