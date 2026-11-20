function phx_plot_results(R, SW, C, outDir)
%PHX_PLOT_RESULTS  Figures of the campaign (same charts as the verification report).
% outcome groups and colours (blue, aqua, violet, grey, dark grey, yellow, red)
G = { [C.O_REC],                     [42 120 214] / 255, 'Detected and recovered';
      [C.O_ECC],                     [27 175 122] / 255, 'Corrected by memory ECC';
      [C.O_RST C.O_SAFE],            [98 80 214] / 255,  'Correct after system reset, or safe state';
      [C.O_NOEFF],                   [195 194 183] / 255,'No effect (overwritten or cleared)';
      [C.O_DUE],                     [143 141 134] / 255,'Flagged by ECC, not correctable';
      [C.O_LAT],                     [237 161 0] / 255,  'Hidden fault left in a core';
      [C.O_WRONG C.O_HANG C.O_CRASH],[227 73 72] / 255,  'Wrong result, hang or crash' };
UN = [C.O_LAT C.O_WRONG C.O_HANG C.O_CRASH];

% ---- Figure 1: outcome by fault class, before and after (stacked bars)
keys = {'core', 'mem1', 'mem2', 'dbl_far', 'dbl_near', 'perm'};
short = {'1 flip, one core', '1 flip, memory word', '2 flips, memory word', ...
         '2 cores, separate times', '2 cores, within 3 cycles', 'Permanent core fault'};
names = {}; M = [];
for e = 1:numel(keys)
    for cname = {'before', 'after'}
        o = R.(keys{e}).(cname{1}).outcome;
        row = zeros(1, size(G, 1));
        for g = 1:size(G, 1), row(g) = 100 * mean(ismember(o, G{g, 1})); end
        M = [M; row]; names{end + 1} = sprintf('%s | %s', short{e}, cname{1}); %#ok<AGROW>
    end
end
f1 = figure('Color', 'w', 'Position', [100 100 1000 620]);
h = barh(M, 'stacked', 'BarWidth', 0.65);
for g = 1:size(G, 1), set(h(g), 'FaceColor', G{g, 2}, 'EdgeColor', 'w'); end
set(gca, 'YTick', 1:numel(names), 'YTickLabel', names, 'YDir', 'reverse', 'XLim', [0 100], 'FontSize', 9);
xlabel('Share of fault-injection runs (%)'); grid on; box off;
title('Outcome by fault class, before and after the three mechanisms');
safe_legend(h, G(:, 3)', 'southoutside', 2);
print(f1, fullfile(outDir, 'fig1_outcomes_by_class.png'), '-dpng', '-r150');

% ---- Figure 2: unresolved runs, before vs after (grouped bars)
k5 = keys(1:5); U = zeros(5, 2);
for e = 1:5
    U(e, 1) = 100 * mean(ismember(R.(k5{e}).before.outcome, UN));
    U(e, 2) = 100 * mean(ismember(R.(k5{e}).after.outcome, UN));
end
f2 = figure('Color', 'w', 'Position', [100 100 900 420]);
b = bar(U, 'grouped');
set(b(1), 'FaceColor', [235 104 52] / 255); set(b(2), 'FaceColor', [42 120 214] / 255);
set(gca, 'XTickLabel', short(1:5), 'FontSize', 9); ylabel('Share of runs (%)'); grid on; box off;
safe_legend(b, {'Before', 'After'}, 'northeast', 1);
title('Unresolved runs: wrong result, hang, or hidden fault left behind');
for e = 1:5
    text(e - 0.15, U(e, 1) + 1.5, sprintf('%.1f%%', U(e, 1)), 'HorizontalAlignment', 'center', 'FontSize', 8);
    text(e + 0.15, U(e, 2) + 1.5, sprintf('%.1f%%', U(e, 2)), 'HorizontalAlignment', 'center', 'FontSize', 8);
end
print(f2, fullfile(outDir, 'fig2_unresolved_before_after.png'), '-dpng', '-r150');

% ---- Figure 3: scrub-period sweep (two separate panels, one measure each)
lab = {'off', '800', '400', '200', '100', '50'};
f3 = figure('Color', 'w', 'Position', [100 100 900 360]);
subplot(1, 2, 1); bar(SW.latent, 0.6, 'FaceColor', [237 161 0] / 255);
set(gca, 'XTickLabel', lab); xlabel('Scrub period (cycles)'); title('Hidden faults left in a core (%)'); grid on; box off;
subplot(1, 2, 2); bar(SW.overhead, 0.6, 'FaceColor', [42 120 214] / 255);
set(gca, 'XTickLabel', lab); xlabel('Scrub period (cycles)'); title('Extra run time, fault-free (%)'); grid on; box off;
print(f3, fullfile(outDir, 'fig3_scrub_sweep.png'), '-dpng', '-r150');
end

function safe_legend(h, labels, loc, ncol)
% Legend that never stops the run (older releases lack NumColumns).
try
    legend(h, labels, 'Location', loc, 'NumColumns', ncol);
catch
    try
        legend(h, labels, 'Location', loc);
    catch
        warning('Legend could not be drawn; the figure is saved without it.');
    end
end
end
