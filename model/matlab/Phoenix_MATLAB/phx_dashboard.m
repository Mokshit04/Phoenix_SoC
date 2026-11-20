function phx_dashboard(R, SW, C)
%PHX_DASHBOARD  One figure with the four campaign results that matter most.
%   1 single core vs three cores, one flip in a core   2 unresolved runs, before vs after
%   3 detection latency, before vs after               4 scrub period: protection vs cost
BLUE = [42 120 214] / 255; ORANGE = [235 104 52] / 255; YELLOW = [237 161 0] / 255;
GREY = [195 194 183] / 255; RED = [227 73 72] / 255;
UN = [C.O_LAT C.O_WRONG C.O_HANG C.O_CRASH];
figure('Color', 'w', 'Position', [40 40 1300 760], 'Name', 'Phoenix campaign dashboard');

% ---- 1. what happens to one flip in a core
subplot(2, 3, 1);
cfgs = {'single', 'before', 'after'}; M = zeros(3, 4);
for k = 1:3
    o = R.core.(cfgs{k}).outcome;
    M(k, :) = 100 * [mean(o == C.O_REC), mean(o == C.O_NOEFF), mean(o == C.O_LAT), ...
                     mean(ismember(o, [C.O_WRONG C.O_HANG C.O_CRASH]))];
end
h = bar(M, 'stacked');
cols = {BLUE, GREY, YELLOW, RED};
for k = 1:4, set(h(k), 'FaceColor', cols{k}, 'EdgeColor', 'w'); end
set(gca, 'XTickLabel', {'1 core', '3 cores, before', '3 cores, after'}, 'FontSize', 9); ylim([0 100]);
ylabel('Share of runs (%)'); title('One bit flip in a core'); grid on; box off;
seg = {'recovered', 'no effect', 'hidden', 'failed'};   % failed = wrong result, hang or crash
txtc = {'w', 'k', 'k', 'w'};
for b1 = 1:3                                   % label each segment directly (no legend needed)
    base = 0;
    for k = 1:4
        if M(b1, k) >= 8
            text(b1, base + M(b1, k) / 2, sprintf('%s %.0f%%', seg{k}, M(b1, k)), ...
                 'HorizontalAlignment', 'center', 'FontSize', 8, 'Color', txtc{k}, 'FontWeight', 'bold');
        end
        base = base + M(b1, k);
    end
end

% ---- 2. unresolved, every class
subplot(2, 3, [2 3]);
keys = {'core', 'mem1', 'mem2', 'dbl_far', 'dbl_near'};
lab = {'1 flip, core', '1 flip, memory', '2 flips, memory', '2 cores, apart', '2 cores, together'};
U = zeros(5, 2);
for e = 1:5
    U(e, :) = 100 * [mean(ismember(R.(keys{e}).before.outcome, UN)), mean(ismember(R.(keys{e}).after.outcome, UN))];
end
b = bar(U, 'grouped'); set(b(1), 'FaceColor', ORANGE); set(b(2), 'FaceColor', BLUE);
set(gca, 'XTickLabel', lab, 'FontSize', 9); ylabel('Share of runs (%)'); grid on; box off;
title('Unresolved runs (wrong result, hang, or hidden fault): before vs after');
legend({'Before', 'After (scrub + ECC + watchdog)'}, 'Location', 'northeast');
for e = 1:5
    text(e - 0.15, U(e, 1) + 2, sprintf('%.1f', U(e, 1)), 'HorizontalAlignment', 'center', 'FontSize', 8);
    text(e + 0.15, U(e, 2) + 2, sprintf('%.1f', U(e, 2)), 'HorizontalAlignment', 'center', 'FontSize', 8);
end
ylim([0 85]);

% ---- 3. detection latency
subplot(2, 3, 4);
edges = [0 10 25 50 100 200 400 800 1600 1e9];
lb = R.core.before.latency; lb = lb(lb >= 0); la = R.core.after.latency; la = la(la >= 0);
hb = histc(lb, edges); ha = histc(la, edges);
H = 100 * [hb(1:end-1)' / numel(lb), ha(1:end-1)' / numel(la)];
b3 = bar(H, 'grouped'); set(b3(1), 'FaceColor', ORANGE); set(b3(2), 'FaceColor', BLUE);
set(gca, 'XTickLabel', {'0', '10', '25', '50', '100', '200', '400', '800', '1600+'}, 'FontSize', 8);
xlabel('Cycles from fault to detection (bin start)'); ylabel('Share of detected faults (%)'); grid on; box off;
title(sprintf('Detection latency  (max %d -> %d cycles)', max(lb), max(la)));
legend({'Before', 'After'}, 'Location', 'northeast');

% ---- 4 and 5. scrub trade-off: two panels, one measure each
lab6 = {'off', '800', '400', '200', '100', '50'};
subplot(2, 3, 5);
bar(SW.latent, 0.6, 'FaceColor', YELLOW); set(gca, 'XTickLabel', lab6, 'FontSize', 9);
xlabel('Scrub period (cycles)'); ylabel('%'); title('Hidden faults left in a core'); grid on; box off;
subplot(2, 3, 6);
bar(SW.overhead, 0.6, 'FaceColor', BLUE); set(gca, 'XTickLabel', lab6, 'FontSize', 9);
xlabel('Scrub period (cycles)'); ylabel('%'); title('Extra run time (fault-free)'); grid on; box off;
end
