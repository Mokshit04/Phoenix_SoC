function phx_plot_timeline(T, res, fault_cycle, ttl, animate)
%PHX_PLOT_TIMELINE  Cycle-by-cycle picture of one run (from phx_run_trace).
%   Row 1: does each core's output agree with the vote?  (green yes, red no, grey in reset)
%   Row 2: is the internal state of the three cores identical? (shows hidden faults)
%   Row 3: PHX_RM state machine
%   Row 4: the two control signals PHX_RM drives: interrupt and core reset
%   Vertical lines mark: fault injected, detected, reset, verified.
if nargin < 5, animate = false; end
GREEN = [27 175 122] / 255; RED = [227 73 72] / 255; GREY = [0.80 0.80 0.78];
BLUE = [42 120 214] / 255; ORANGE = [235 104 52] / 255; INK = [0.15 0.15 0.15];

% ---- window: a little before the fault to a little after the recovery
t_det = res.rm.t_detect; t_ok = res.rm.t_recovered;
x0 = max(0, fault_cycle - 40);
if t_ok >= 0, x1 = t_ok + 60; elseif t_det >= 0, x1 = t_det + 400; else, x1 = T.cycle(end); end
x1 = min(x1, T.cycle(end));
w = (T.cycle >= x0) & (T.cycle <= x1);
cyc = T.cycle(w);

fig = figure('Color', 'w', 'Position', [60 60 1200 680], 'Name', ttl);
% ---- row 1: agreement strip
ax1 = subplot(4, 1, 1);
A = T.agree(:, w); img = A; img(isnan(A)) = 2;          % 0 disagree, 1 agree, 2 reset
imagesc(cyc, 1:size(A, 1), img, [0 2]); colormap(ax1, [RED; GREEN; GREY]);
set(ax1, 'YTick', 1:size(A, 1), 'YTickLabel', {'Core A', 'Core B', 'Core C'}, 'TickLength', [0 0]);
title(ax1, 'Does each core''s output agree with the vote?   green = yes, red = no, grey = held in reset');
% ---- row 2: internal state identical
ax2 = subplot(4, 1, 2);
stairs(cyc, T.same(w), 'Color', INK, 'LineWidth', 2.5); ylim([-0.2 1.2]);
set(ax2, 'YTick', [0 1], 'YTickLabel', {'different', 'identical'});
title(ax2, 'Internal state of the three cores (registers, program counter)');
% ---- row 3: PHX_RM state
ax3 = subplot(4, 1, 3);
stairs(cyc, T.rm_state(w), 'Color', BLUE, 'LineWidth', 2.5); ylim([-0.5 5.5]);
set(ax3, 'YTick', 0:5, 'YTickLabel', {'Monitor', 'Save', 'Reset', 'Restore', 'Verify', 'Safe'});
title(ax3, 'PHX\_RM recovery manager state');
% ---- row 4: control signals
ax4 = subplot(4, 1, 4);
stairs(cyc, T.irq(w) + 1.5, 'Color', ORANGE, 'LineWidth', 2); hold on;
stairs(cyc, T.reset(w), 'Color', RED, 'LineWidth', 2); hold off; ylim([-0.3 2.8]);
set(ax4, 'YTick', [0.5 2], 'YTickLabel', {'core reset', 'interrupt'});
xlabel(ax4, 'Clock cycle'); title(ax4, 'Signals from PHX\_RM to the cores');
AX = [ax1 ax2 ax3 ax4];
for a = AX, set(a, 'XLim', [x0 - 0.5, x1 + 0.5], 'Box', 'off', 'FontSize', 9); grid(a, 'on'); end

% ---- event markers
ev = {fault_cycle, 'fault injected'};
if t_det >= 0, ev(end + 1, :) = {t_det, 'detected'}; end
r = find(T.reset == 1 & T.cycle >= max(t_det, 0), 1);
if ~isempty(r) && t_det >= 0, ev(end + 1, :) = {T.cycle(r), 'reset'}; end
if t_ok >= 0, ev(end + 1, :) = {t_ok, 'verified'}; end
key = '';
for e = 1:size(ev, 1)
    for a = AX
        yl = get(a, 'YLim');
        line(a, [ev{e, 1} ev{e, 1}], yl, 'Color', [0.3 0.3 0.3], 'LineStyle', '--', 'LineWidth', 1);
    end
    % numbered marker at the top of row 1 (staggered so close events stay readable)
    yl = get(ax1, 'YLim');
    ytop = yl(1) + (0.18 + 0.30 * mod(e - 1, 2)) * diff(yl) / 3;
    text(ax1, ev{e, 1}, ytop, sprintf(' %d ', e), 'FontSize', 9, 'FontWeight', 'bold', ...
         'BackgroundColor', 'w', 'EdgeColor', [0.3 0.3 0.3], 'HorizontalAlignment', 'center');
    key = [key sprintf('%d = %s (cycle %d)    ', e, ev{e, 2}, ev{e, 1})]; %#ok<AGROW>
end

% ---- summary line under the title of the window
L = phx_labels();
s = sprintf('%s  |  outcome: %s', ttl, L{res.outcome});
if res.latency >= 0, s = [s sprintf('  |  detected %d cycles after the fault', res.latency)]; end
if res.recovery >= 0, s = [s sprintf('  |  recovered and verified in %d cycles', res.recovery)]; end
set(fig, 'Name', s);
try
    sgtitle(fig, {s, strtrim(key)}, 'FontSize', 11, 'FontWeight', 'bold');
catch
    title(ax1, {s, strtrim(key), get(get(ax1, 'Title'), 'String')});
end

% ---- optional animation: a cursor sweeps through the cycles
if animate
    cur = gobjects(1, numel(AX));
    for k = 1:numel(AX)
        cur(k) = line(AX(k), [x0 x0], get(AX(k), 'YLim'), 'Color', BLUE, 'LineWidth', 2.5);
    end
    for x = x0:2:x1
        for k = 1:numel(AX), set(cur(k), 'XData', [x x]); end
        drawnow; pause(0.01);
    end
end
end
