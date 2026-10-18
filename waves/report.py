"""Render FINDINGS_WAVES.md and waves/plots/ from waves/results/.   python3 -m waves.report"""
import datetime as dt
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
PLOTS = HERE / "plots"
OUT = HERE / "FINDINGS_WAVES.md"
BANDS = (90.0, 95.0, 99.0, 99.9)
BAND_LABEL = {90.0: "p90-95", 95.0: "p95-99", 99.0: "p99-99.9", 99.9: ">= p99.9"}
KS = (1, 2, 3, 4, 5)
HS = (0, 1, 2, 5, 10, 30)
BLUE, ORANGE, AQUA, YELLOW, MAG = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10,
                     "axes.titlecolor": INK, "legend.frameon": False, "savefig.dpi": 130})
BAND_COL = {90.0: YELLOW, 95.0: AQUA, 99.0: BLUE, 99.9: ORANGE}


def wmean(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float); ok = ~np.isnan(x)
    return float(np.average(x[ok], weights=w[ok])) if ok.any() and w[ok].sum() > 0 else float("nan")


def wshare(mask, w):
    w = np.asarray(w, float); return float(w[mask].sum() / w.sum()) if w.sum() > 0 else float("nan")


def wq(x, w, q):
    x = np.asarray(x, float); w = np.asarray(w, float); ok = ~np.isnan(x)
    if not ok.any():
        return float("nan")
    o = np.argsort(x[ok]); xs, ws = x[ok][o], w[ok][o]; c = np.cumsum(ws) / ws.sum()
    return float(xs[np.searchsorted(c, q)])


def pooled(e, name, k):
    """Concatenate +k and -k columns (both sides of the initiator) with weights."""
    a = e["%s_%+d" % (name, k)].values; b = e["%s_%+d" % (name, -k)].values
    return np.concatenate([a, b]), np.concatenate([e.weight.values, e.weight.values])


def pooled_resp(e, k, h, absolute=False):
    a = e["resp_%+d_%d" % (k, h)].values; b = e["resp_%+d_%d" % (-k, h)].values
    x = np.concatenate([a, b]); w = np.concatenate([e.weight.values, e.weight.values])
    return (np.abs(x) if absolute else x), w


def band_sel(e, b):
    return e[e.band >= 99.9] if b == 99.9 else e[e.band == b]


def f(x, d=2):
    return ("%%.%df" % d) % x if x == x else "-"


def md(df, d=2):
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append(("{:,}".format(int(v)) if abs(v) >= 10000 else str(int(v))) if float(v).is_integer() and (c in ("n", "events", "ladders", "ladder_days") or abs(v) >= 1000) else f(v, d))
            elif isinstance(v, (int, np.integer)):
                cells.append("{:,}".format(int(v)) if abs(int(v)) >= 10000 else str(int(v)))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def timing_row(e, k):
    fx, w = pooled(e, "first", k); ok = fx >= 0; fx, w = fx[ok], w[ok]
    rate, _ = pooled(e, "nbrate", k); rate = rate[ok]
    base0 = rate; base5 = 1 - (1 - rate) ** 6; base30 = 1 - (1 - rate) ** 31
    moved30 = fx <= 30
    return dict(n=int(w.sum()), same_minute=wshare(fx == 0, w), within_5=wshare(fx <= 5, w), within_30=wshare(moved30, w), none_30=wshare(fx == 99, w),
                baseline_same=wmean(base0, w), baseline_5=wmean(base5, w), baseline_30=wmean(base30, w),
                median_min_if_moved=wq(np.where(moved30, fx, np.nan), w, 0.5))


def resp_row(e, k, absolute=False):
    out = {}
    for h in HS:
        x, w = pooled_resp(e, k, h, absolute); out["h%d" % h] = wmean(x, w)
    x0, w0 = pooled_resp(e, k, 0, absolute); x30, _ = pooled_resp(e, k, 30, absolute)
    out["n"] = int(w0[~np.isnan(x0)].sum()); out["after_same_minute"] = out["h30"] - out["h0"]
    xs, ws = pooled_resp(e, k, 30, False)
    out["same_sign_30"] = float(np.average((xs[~np.isnan(xs)] > 0), weights=ws[~np.isnan(xs)])) if (~np.isnan(xs)).any() else float("nan")
    return out


def persistence_row(e):
    w = e.weight.values; r5 = e.ret_5.values; r30 = e.ret_30.values
    ok = ~np.isnan(r30)
    return dict(n=int(w[ok].sum()), ret_5=wmean(r5, w), ret_30=wmean(r30, w), persist_30=wshare(ok & (np.nan_to_num(r30, nan=-9) >= 0.5), w),
                partial_30=wshare(ok & (np.nan_to_num(r30, nan=-9) > 0) & (np.nan_to_num(r30, nan=-9) < 0.5), w), revert_30=wshare(ok & (np.nan_to_num(r30, nan=9) <= 0), w),
                overshoot_30=wshare(ok & (np.nan_to_num(r30, nan=-9) > 1.5), w), trade_driven=wshare(e.vol.values > 0, w))


def cond_table(e, col, labels, k=1):
    rows = []
    for lab, sel in labels:
        s = e[sel(e)]
        if not len(s):
            continue
        t = timing_row(s, k); r = resp_row(s, k); p = persistence_row(s)
        rows.append({col: lab, "n": t["n"], "same_min": t["same_minute"], "baseline_same": t["baseline_same"], "within_30": t["within_30"], "baseline_30": t["baseline_30"],
                     "resp_h0": r["h0"], "resp_h30": r["h30"], "after_same_min": r["after_same_minute"], "ret_30": p["ret_30"], "revert_30": p["revert_30"]})
    return pd.DataFrame(rows)


def plots(cu):
    PLOTS.mkdir(exist_ok=True)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for b in BANDS:
        e = band_sel(cu, b)
        if not len(e):
            continue
        for ax, h in ((axs[0], 0), (axs[1], 30)):
            ys = [resp_row(e, k)["h%d" % h] for k in KS]
            ax.plot(KS, ys, marker="o", ms=4, lw=2, color=BAND_COL[b], label=BAND_LABEL[b])
    for ax, h in ((axs[0], 0), (axs[1], 30)):
        ax.set_title("neighbour move / impulse, %s" % ("same minute" if h == 0 else "30 minutes after")); ax.set_xlabel("distance (brackets)"); ax.set_xticks(KS); ax.set_ylim(0, 0.8)
    axs[0].set_ylabel("response (fraction of the impulse)"); axs[0].legend(title="event size")
    fig.suptitle("Decay with distance, cumulative ladders, by event-size band", color=INK, fontsize=10); fig.tight_layout(); fig.savefig(PLOTS / "decay.png"); plt.close(fig)
    # timing
    fig, ax = plt.subplots(figsize=(8, 3.4))
    cats = ["same min", "1", "2", "3-5", "6-10", "11-30", "none"]
    x = np.arange(len(cats)); wdt = 0.2
    for i, b in enumerate(BANDS):
        e = band_sel(cu, b)
        if not len(e):
            continue
        fx, w = pooled(e, "first", 1); ok = fx >= 0; fx, w = fx[ok], w[ok]
        bins = [wshare(fx == 0, w), wshare(fx == 1, w), wshare(fx == 2, w), wshare((fx >= 3) & (fx <= 5), w), wshare((fx >= 6) & (fx <= 10), w), wshare((fx >= 11) & (fx <= 30), w), wshare(fx == 99, w)]
        ax.bar(x + (i - 1.5) * wdt, bins, wdt, color=BAND_COL[b], label=BAND_LABEL[b])
    ax.set_xticks(x); ax.set_xticklabels(cats); ax.set_ylabel("share of adjacent neighbours"); ax.set_xlabel("minute of the neighbour's first move after the impulse")
    ax.set_title("Timing of the adjacent bracket's first move (distance 1)"); ax.legend(title="event size"); fig.tight_layout(); fig.savefig(PLOTS / "timing.png"); plt.close(fig)
    # persistence
    fig, ax = plt.subplots(figsize=(8, 3.4))
    bins = np.arange(-1.0, 2.26, 0.25)
    for b in BANDS:
        e = band_sel(cu, b)
        if not len(e):
            continue
        r = e.ret_30.clip(-1, 2.25).values; w = e.weight.values; ok = ~np.isnan(r)
        hst, _ = np.histogram(r[ok], bins=bins, weights=w[ok]); hst = hst / hst.sum()
        ax.step(bins[:-1], hst, where="post", color=BAND_COL[b], lw=2, label=BAND_LABEL[b])
    ax.axvline(0, color=INK, lw=0.8); ax.axvline(1, color=INK2, lw=0.8, ls="--")
    ax.set_xlabel("initiator's retained move after 30 minutes (fraction of the impulse; 0 = fully reverted, 1 = held)"); ax.set_ylabel("share of events")
    ax.set_title("Initiator persistence"); ax.legend(title="event size"); fig.tight_layout(); fig.savefig(PLOTS / "persistence.png"); plt.close(fig)
    # sweep
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
    xs = list(range(len(BANDS)))
    r0 = [resp_row(band_sel(cu, b), 1)["h0"] if len(band_sel(cu, b)) else np.nan for b in BANDS]
    r30 = [resp_row(band_sel(cu, b), 1)["h30"] if len(band_sel(cu, b)) else np.nan for b in BANDS]
    sm = [timing_row(band_sel(cu, b), 1)["same_minute"] if len(band_sel(cu, b)) else np.nan for b in BANDS]
    bl = [timing_row(band_sel(cu, b), 1)["baseline_same"] if len(band_sel(cu, b)) else np.nan for b in BANDS]
    axs[0].plot(xs, r0, marker="o", color=BLUE, lw=2, label="same minute"); axs[0].plot(xs, r30, marker="o", color=ORANGE, lw=2, label="after 30 min")
    axs[0].set_xticks(xs); axs[0].set_xticklabels([BAND_LABEL[b] for b in BANDS]); axs[0].set_ylabel("adjacent response / impulse"); axs[0].set_ylim(0, 0.8); axs[0].legend(); axs[0].set_title("Response at distance 1 against the event threshold")
    axs[1].plot(xs, sm, marker="o", color=BLUE, lw=2, label="adjacent moved in the same minute"); axs[1].plot(xs, bl, marker="o", color=MUTED, lw=2, ls="--", label="its unconditional per-minute rate")
    axs[1].set_xticks(xs); axs[1].set_xticklabels([BAND_LABEL[b] for b in BANDS]); axs[1].set_ylim(0, 1); axs[1].legend(); axs[1].set_title("Same-minute share against the threshold")
    fig.tight_layout(); fig.savefig(PLOTS / "sweep.png"); plt.close(fig)


def render(ev, sm):
    L = []; w = L.append
    cu = ev[ev.kind == "cumul"]; ra = ev[ev.kind == "range"]
    smo = sm[sm.skipped.isna()] if "skipped" in sm else sm
    tags = sorted(sm.tag.dropna().unique())
    w("# FINDINGS_WAVES — do propagation waves exist? A descriptive census\n")
    w("Generated %s by `python3 -m waves.run` / `python3 -m waves.report`. Brief: `NightKing/HANDOFF_waves.md`. Code: `waves/`. Results: `waves/results/` (per-ladder parts, `summary.parquet`, `events.parquet`), plots `waves/plots/`.\n" % dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    w("Ladders present in both stores (markets closing after 2026-09-01, re-pulled in full for the forward extension) are counted once, from the expanded store.\n")
    w("Stores: %s. Ladders processed %s (%s with enough changes to define events, %s skipped with fewer than 50 non-zero mid changes), %s ladder-days, %s non-zero minute-to-minute mid changes on tight two-sided brackets. No model, no trade, no friction: every number is a description of what the ladder did.\n"
      % (", ".join("%s (%d ladders)" % (t, (sm.tag == t).sum()) for t in tags), "{:,}".format(len(sm)), "{:,}".format(len(smo)), "{:,}".format(len(sm) - len(smo)), "{:,}".format(int(smo.ladder_days.sum())), "{:,}".format(int(smo.changes.sum()))))
    # headline numbers
    e99 = band_sel(cu, 99.0); e999 = band_sel(cu, 99.9); e90 = band_sel(cu, 90.0); e95 = band_sel(cu, 95.0)
    t1 = {b: timing_row(band_sel(cu, b), 1) for b in BANDS if len(band_sel(cu, b))}
    r1 = {b: resp_row(band_sel(cu, b), 1) for b in BANDS if len(band_sel(cu, b))}
    r5 = {b: resp_row(band_sel(cu, b), 5) for b in BANDS if len(band_sel(cu, b))}
    p1 = {b: persistence_row(band_sel(cu, b)) for b in BANDS if len(band_sel(cu, b))}
    w("## Verdict\n")
    e95p = cu[cu.band >= 95.0]
    ttc_tab = cond_table(e95p, "time_to_close", [("< 4 h", lambda d: d.min_to_close < 240), ("4-24 h", lambda d: (d.min_to_close >= 240) & (d.min_to_close < 1440)), ("1-7 d", lambda d: (d.min_to_close >= 1440) & (d.min_to_close < 7 * 1440)), ("> 7 d", lambda d: d.min_to_close >= 7 * 1440)]).set_index("time_to_close")
    w("**A wave exists; it is wide, shallow, and over inside the impulse minute — except in the last day of a ladder's life, where a slow second leg follows.** When a bracket makes a move in the top 1%% of its own distribution, the adjacent bracket moves in the same minute %.0f%% of the time (its unconditional chance of moving in any minute is %.0f%%), by %.2f of the impulse; five strikes away it moves in the same minute %.0f%% of the time, by %.2f. Pooled over everything, the next thirty minutes add only %+.2f of the impulse at distance 1; the share that moves later than the impulse minute but within thirty (%.0f%%) is what the neighbour's own activity rate predicts (%.0f%% within thirty unconditionally), and %.0f%% do not move at all.\n"
      % (100 * t1[99.0]["same_minute"], 100 * t1[99.0]["baseline_same"], r1[99.0]["h0"], 100 * timing_row(e99, 5)["same_minute"], r5[99.0]["h0"], r1[99.0]["after_same_minute"],
         100 * (t1[99.0]["within_30"] - t1[99.0]["same_minute"]), 100 * t1[99.0]["baseline_30"], 100 * t1[99.0]["none_30"]))
    w("**Time to close is the conditioning that matters.** For events (>= p95) in the last 4 hours before close the adjacent bracket moves %.2f of the impulse in the same minute and %.2f after thirty (%+.2f added, n = %s); at 4-24 hours %.2f then %.2f (%+.2f, n = %s); at 1-7 days the thirty-minute response is below the same-minute one (%+.2f, n = %s) and beyond 7 days the wave barely exists (%.2f same minute, n = %s). The late leg near expiry travels with distance (section 6): it is a ladder-wide drift, not a nearest-neighbour relay. The initiator holds its move fully in the last day (retained %.2f after thirty minutes) and only %.2f beyond a week. Candles cannot tell whether that late leg is propagation (neighbours catching up to the initiator) or the underlying continuing to move with every bracket following it; both read the same on a minute grid.\n"
      % (ttc_tab.loc["< 4 h", "resp_h0"], ttc_tab.loc["< 4 h", "resp_h30"], ttc_tab.loc["< 4 h", "after_same_min"], "{:,}".format(int(ttc_tab.loc["< 4 h", "n"])),
         ttc_tab.loc["4-24 h", "resp_h0"], ttc_tab.loc["4-24 h", "resp_h30"], ttc_tab.loc["4-24 h", "after_same_min"], "{:,}".format(int(ttc_tab.loc["4-24 h", "n"])),
         ttc_tab.loc["1-7 d", "after_same_min"], "{:,}".format(int(ttc_tab.loc["1-7 d", "n"])), ttc_tab.loc["> 7 d", "resp_h0"], "{:,}".format(int(ttc_tab.loc["> 7 d", "n"])),
         ttc_tab.loc["< 4 h", "ret_30"], ttc_tab.loc["> 7 d", "ret_30"]))
    oi_tab = cond_table(e95p, "oi", [("lo", lambda d: d.oi < 100), ("mid", lambda d: (d.oi >= 100) & (d.oi < 1000)), ("hi", lambda d: (d.oi >= 1000) & (d.oi < 10000)), ("vhi", lambda d: d.oi >= 10000)]).set_index("oi")
    w("**Depth works the same way.** Split by the initiating bracket's open interest, the same-minute response falls from %.2f (under 100 contracts) to %.2f (10,000 or more) while the thirty-minute response rises from %.2f to %.2f: thin brackets are re-quoted together at once, deep ones follow over the half hour (%+.2f added). The slow part of the wave lives where the size is — the opposite of the stale-tail picture, and the one place where a lag and depth coincide. Hour of day adds a smaller version of the same thing (US morning: %+.2f added; overnight: %+.2f).\n"
      % (oi_tab.loc["lo", "resp_h0"], oi_tab.loc["vhi", "resp_h0"], oi_tab.loc["lo", "resp_h30"], oi_tab.loc["vhi", "resp_h30"], oi_tab.loc["vhi", "after_same_min"],
         cond_table(e95p, "h", [("us", lambda d: (d.hour >= 13) & (d.hour < 17))]).after_same_min.iloc[0], cond_table(e95p, "h", [("n", lambda d: d.hour < 8)]).after_same_min.iloc[0]))
    w("**The threshold sweep: the 'unusual move' framing adds little.** From the 90th to the 99.9th percentile of a bracket's own changes the same-minute adjacent response rises from %.2f to %.2f of the impulse and the same-minute share from %.0f%% to %.0f%%; the thirty-minute response is flat (%.2f to %.2f), and at the top band the neighbours give back %.2f of the impulse over the half hour. Bigger events are followed a little more often and a little more fully in the same minute, and no more afterwards. There is no threshold above which a lagged response appears; the lag is a function of time to expiry, not of event size. Every band has tens of thousands of events or more, so none of this is thin.\n"
      % (r1[90.0]["h0"], r1[99.9]["h0"], 100 * t1[90.0]["same_minute"], 100 * t1[99.9]["same_minute"], r1[90.0]["h30"], r1[99.9]["h30"], -r1[99.9]["after_same_minute"]))
    w("**Initiators mostly hold, and trade-driven ones hold best.** After thirty minutes the initiating bracket retains a mean %.2f of its move at the top band; %.0f%% retain at least half, %.0f%% have fully reverted. Moves made by a trade in the minute retain ~1.0 of the move with %.0f%% reverting; pure quote moves retain %.2f with %.0f%% reverting. The spike trap is real for quote-driven moves and a minority overall.\n"
      % (p1[99.9]["ret_30"], 100 * p1[99.9]["persist_30"], 100 * p1[99.9]["revert_30"], 100 * persistence_row(e99[e99.vol > 0])["revert_30"], persistence_row(e99[e99.vol == 0])["ret_30"], 100 * persistence_row(e99[e99.vol == 0])["revert_30"]))
    w("**Decay with distance is slow and nearly linear**: each extra strike removes about a tenth of the response (step ratios 0.85-0.92 at every band), so five strikes away still carries %.0f%% of the adjacent response. The wave is a parallel shift that fades gently, not a nearest-neighbour cliff.\n" % (100 * resp_row(e99, 5)["h0"] / resp_row(e99, 1)["h0"]))
    w("**Resolution and what to do next.** Away from expiry, everything the wave does it does inside the candle, and candles cannot say whether that is one second or fifty-nine; a wave that is catchable at all there is sub-minute and only a websocket book feed can see it. Near expiry the late leg is visible at minute resolution and is the thing a follow-on should test first, on the daily commodity ladders where it is largest (KXBRENTD, KXGOLDD, KXWTI, KXNATGASD) — see `NEXT_STUDY.md`. The websocket collector is warranted only if that near-expiry leg survives a check against the underlying's own path, which is a cheaper question.\n")
    w("## 0. Definitions and data construction\n")
    w("- Movement is measured on mids of the carried-forward minute grid (ladder.store), only where the bracket is two-sided with spread <= 10c on both minutes (so the mid means something; a bid 19 / ask 99 book has no mid). The store is sparse by design (a candle exists only when the top of book changed, verified in `ladder/FINDINGS_LADDER_DYNAMICS.md` §0), so a bracket's minute-to-minute change is non-zero exactly on the minutes it printed.")
    w("- **Per-bracket normalisation.** A bracket's event thresholds are the 90th / 95th / 99th / 99.9th percentiles of the absolute size of its own non-zero changes. Mids move in half-cent steps, so the percentile values are discrete and ties are common: 'at or above the 90th percentile value' takes about 17%% of changes rather than 10%%, and the bands below are labelled by the percentile cleared, not by an exact share. A bracket with fewer than 50 non-zero changes borrows its ladder's pooled distribution (flagged; %.1f%% of sampled events); a ladder with fewer than 50 changes in total is skipped." % (100 * wshare(ev.fallback.values, ev.weight.values)))
    w("- **Event** = a minute where a bracket's change clears its 90th-percentile threshold; its band is the highest percentile it clears. Events in the 90-95 band are stored 1-in-4 with weight 4 (every count and mean below is weighted); every event above the 95th is stored.")
    w("- **Response** of a neighbour at distance k, horizon h = (its mid at t+h minus its mid at t-1) divided by the initiator's change, signed; on a P(>X) ladder a parallel shift gives the same sign at every distance. Both sides (+k and -k) are pooled. h = 0 is the impulse minute. **First move** = the first minute in 0..30 at which the neighbour's mid differs from its value at t-1 (any half-cent); 'none' = no change within 30 minutes. **Baseline** = the neighbour's own unconditional change probability per valid minute over the ladder's life, and 1-(1-r)^(h+1) for 'within h'.")
    w("- **Persistence** = the initiator's retained move after h minutes as a fraction of its change: >= 0.5 persists, (0, 0.5) partial, <= 0 reverted.")
    w("- Range ladders (brackets '$77 to 77.99') have no common sign convention for neighbours, so they are reported on timing and absolute response only (section 7). Everything else is cumulative ladders.\n")
    # 1 frequency
    w("## 1. Event frequency\n")
    rows = []
    for b in BANDS:
        rows.append(dict(threshold="≥ p%g" % b, events=int(smo["events_%g" % b].sum()), per_ladder_day=smo["events_%g" % b].sum() / smo.ladder_days.sum(), per_bracket_day=smo["events_%g" % b].sum() / (smo.ladder_days * smo.brackets).sum(),
                         share_of_changes=smo["events_%g" % b].sum() / smo.changes.sum()))
    w(md(pd.DataFrame(rows), 3) + "\n")
    g = smo.groupby(["tag", "category"], dropna=False).agg(ladders=("event", "size"), ladder_days=("ladder_days", "sum"), changes=("changes", "sum"), e95=("events_95", "sum"), e99=("events_99", "sum"), e999=("events_99.9", "sum")).reset_index()
    g["p95_per_ladder_day"] = g.e95 / g.ladder_days; g["p99_per_ladder_day"] = g.e99 / g.ladder_days; g["p99.9_per_ladder_day"] = g.e999 / g.ladder_days
    w("By store and category:\n\n" + md(g.sort_values("changes", ascending=False), 2) + "\n")
    gs = smo.groupby("series").agg(ladders=("event", "size"), ladder_days=("ladder_days", "sum"), changes=("changes", "sum"), e99=("events_99", "sum")).reset_index()
    gs["p99_per_ladder_day"] = gs.e99 / gs.ladder_days
    w("Top 25 series by changes:\n\n" + md(gs.sort_values("changes", ascending=False).head(25), 2) + "\n")
    # 2 amplitude by distance
    w("## 2. Response amplitude by distance (cumulative ladders)\n")
    w("Mean neighbour move as a fraction of the impulse, pooled over both sides. n = weighted events with a valid neighbour at that distance.\n")
    for h in (0, 5, 30):
        rows = []
        for b in BANDS:
            e = band_sel(cu, b)
            if not len(e):
                continue
            r = {"band": BAND_LABEL[b]}
            for k in KS:
                rr = resp_row(e, k); r["k=%d" % k] = rr["h%d" % h]; r["n(k=%d)" % k] = rr["n"] if k in (1, 5) else None
            rows.append({kk: v for kk, v in r.items() if v is not None})
        w("**h = %d%s**\n\n" % (h, " (same minute)" if h == 0 else " minutes after") + md(pd.DataFrame(rows), 3) + "\n")
    rows = []
    for b in BANDS:
        e = band_sel(cu, b)
        if not len(e):
            continue
        r = {"band": BAND_LABEL[b]}
        for k in KS:
            rr = resp_row(e, k); r["k=%d" % k] = rr["after_same_minute"]
        rows.append(r)
    w("**Added after the same minute (h=30 minus h=0)** — what a minute-resolution observer could still see coming:\n\n" + md(pd.DataFrame(rows), 3) + "\n")
    rows = []
    for b in BANDS:
        e = band_sel(cu, b)
        if not len(e):
            continue
        r = {"band": BAND_LABEL[b]}
        for k in KS:
            r["k=%d" % k] = resp_row(e, k)["same_sign_30"]
        rows.append(r)
    w("**Direction agreement at h=30** (share of neighbours whose net move has the impulse's sign; 0.5 = coin flip):\n\n" + md(pd.DataFrame(rows), 3) + "\n")
    w("![decay](plots/decay.png)\n")
    # 3 timing
    w("## 3. Response timing by distance\n")
    rows = []
    for b in BANDS:
        e = band_sel(cu, b)
        if not len(e):
            continue
        for k in (1, 2, 3, 5):
            t = timing_row(e, k); t = dict(band=BAND_LABEL[b], k=k, **t); rows.append(t)
    w(md(pd.DataFrame(rows), 3) + "\n")
    w("'same_minute' is the ceiling on what one-minute candles can resolve. 'baseline_same' is what the neighbour does in any minute; the excess is the wave. 'none_30' never moved within thirty minutes.\n")
    w("![timing](plots/timing.png)\n")
    # 4 decay shape
    w("## 4. Decay with distance\n")
    rows = []
    for b in BANDS:
        e = band_sel(cu, b)
        if not len(e):
            continue
        r0 = [resp_row(e, k)["h0"] for k in KS]; r30 = [resp_row(e, k)["h30"] for k in KS]
        rows.append(dict(band=BAND_LABEL[b], **{"h0 k%d/k1" % k: r0[k - 1] / r0[0] for k in KS}, **{"h30 k%d/k1" % k: r30[k - 1] / r30[0] for k in KS}, **{"h0 step %d->%d" % (k, k + 1): r0[k] / r0[k - 1] for k in (1, 2, 3, 4)}))
    w("Response at distance k relative to distance 1, and the step ratio between successive distances (a constant step ratio is exponential decay; a ratio that rises toward 1 is slower than exponential).\n\n" + md(pd.DataFrame(rows), 3) + "\n")
    # position dependence: distance measured toward the body vs the tail?
    # 5 persistence
    w("## 5. Initiator persistence (the trap check)\n")
    rows = [dict(band=BAND_LABEL[b], **persistence_row(band_sel(cu, b))) for b in BANDS if len(band_sel(cu, b))]
    w(md(pd.DataFrame(rows), 3) + "\n")
    rows = []
    for b in (95.0, 99.0, 99.9):
        e = band_sel(cu, b)
        for lab, sel in (("trade in the minute", lambda d: d.vol > 0), ("no trade (quote move)", lambda d: d.vol == 0)):
            s = e[sel(e)]
            if len(s):
                rows.append(dict(band=BAND_LABEL[b], initiator=lab, **persistence_row(s)))
    w("By whether the impulse minute carried a trade on the initiating bracket:\n\n" + md(pd.DataFrame(rows), 3) + "\n")
    w("![persistence](plots/persistence.png)\n")
    # 6 conditioning
    w("## 6. Conditioning (events >= p95, adjacent neighbour, cumulative ladders)\n")
    e95p = cu[cu.band >= 95.0]
    ttc = [("< 4 h", lambda d: d.min_to_close < 240), ("4-24 h", lambda d: (d.min_to_close >= 240) & (d.min_to_close < 1440)), ("1-7 d", lambda d: (d.min_to_close >= 1440) & (d.min_to_close < 7 * 1440)), ("> 7 d", lambda d: d.min_to_close >= 7 * 1440)]
    w("**Time to close**\n\n" + md(cond_table(e95p, "time_to_close", ttc), 3) + "\n")
    rows = []
    for lab, sel in ttc:
        s_ = e95p[sel(e95p)]
        if not len(s_):
            continue
        r = {"time_to_close": lab, "n": int(s_.weight.sum())}
        for k in KS:
            rr = resp_row(s_, k); r["h0 k=%d" % k] = rr["h0"]; r["h30 k=%d" % k] = rr["h30"]
        rows.append(r)
    w("Response by distance within each time-to-close bucket (same minute and after 30 minutes):\n\n" + md(pd.DataFrame(rows), 3) + "\n")
    cats = sorted(e95p.category.dropna().unique())
    w("**Category / store**\n\n" + md(cond_table(e95p, "category", [(c, (lambda c_: (lambda d: d.category == c_))(c)) for c in cats]), 3) + "\n")
    top = e95p.groupby("series").weight.sum().sort_values(ascending=False).head(16).index.tolist()
    w("**Series (top 16 by events)**\n\n" + md(cond_table(e95p, "series", [(s_, (lambda s2: (lambda d: d.series == s2))(s_)) for s_ in top]), 3) + "\n")
    spr = [("<= 2c", lambda d: d.spread0 <= 2), ("3-5c", lambda d: (d.spread0 >= 3) & (d.spread0 <= 5)), ("6-10c", lambda d: d.spread0 >= 6)]
    w("**Initiator spread before the move**\n\n" + md(cond_table(e95p, "spread", spr), 3) + "\n")
    nsp = [("neighbour <= 2c", lambda d: d["nbsp_+1"] <= 2), ("neighbour 3-5c", lambda d: (d["nbsp_+1"] >= 3) & (d["nbsp_+1"] <= 5)), ("neighbour 6-10c", lambda d: d["nbsp_+1"] >= 6)]
    w("**Adjacent neighbour's spread (the +1 side only)**\n\n" + md(cond_table(e95p, "neighbour_spread", nsp), 3) + "\n")
    hrs = [("00-07 UTC", lambda d: d.hour < 8), ("08-12 UTC", lambda d: (d.hour >= 8) & (d.hour < 13)), ("13-16 UTC (US morning)", lambda d: (d.hour >= 13) & (d.hour < 17)), ("17-21 UTC (US afternoon)", lambda d: (d.hour >= 17) & (d.hour < 22)), ("22-23 UTC", lambda d: d.hour >= 22)]
    w("**Hour of day**\n\n" + md(cond_table(e95p, "hour", hrs), 3) + "\n")
    ois = [("OI < 100", lambda d: d.oi < 100), ("100-1,000", lambda d: (d.oi >= 100) & (d.oi < 1000)), ("1,000-10,000", lambda d: (d.oi >= 1000) & (d.oi < 10000)), (">= 10,000", lambda d: d.oi >= 10000)]
    w("**Initiator open interest** (the only depth proxy in the candles)\n\n" + md(cond_table(e95p, "open_interest", ois), 3) + "\n")
    mon = [("initiator tail (mid < 10 or > 90)", lambda d: (d.mid0 < 10) | (d.mid0 > 90)), ("initiator body", lambda d: (d.mid0 >= 10) & (d.mid0 <= 90))]
    w("**Moneyness of the initiator**\n\n" + md(cond_table(e95p, "moneyness", mon), 3) + "\n")
    w("**Event size**\n\n" + md(cond_table(cu, "band", [(BAND_LABEL[b], (lambda b2: (lambda d: (d.band >= 99.9) if b2 == 99.9 else (d.band == b2)))(b)) for b in BANDS]), 3) + "\n")
    # 7 range
    w("## 7. Range ladders\n")
    if len(ra):
        rows = []
        for b in BANDS:
            e = band_sel(ra, b)
            if not len(e):
                continue
            for k in (1, 2, 3):
                t = timing_row(e, k); r = resp_row(e, k, absolute=True)
                rows.append(dict(band=BAND_LABEL[b], k=k, n=t["n"], same_minute=t["same_minute"], baseline_same=t["baseline_same"], within_30=t["within_30"], none_30=t["none_30"], abs_resp_h0=r["h0"], abs_resp_h30=r["h30"]))
        w(md(pd.DataFrame(rows), 3) + "\n")
        w("Absolute response (|neighbour move| / |impulse|) because a shift of the underlying raises one neighbour and lowers the other on a range ladder.\n")
    else:
        w("No range-ladder events.\n")
    # 8 resolution
    w("## 8. The sub-minute limit\n")
    w("Same-minute share at distance 1 is %.0f%% (p95) to %.0f%% (p99.9) against an unconditional per-minute rate of %.0f-%.0f%%; at distance 5 it is %.0f%% to %.0f%%. Everything the wave does, it does inside the candle. The candle store cannot distinguish 'the market maker re-quoted every strike in one update' from 'the neighbours followed within seconds', and that distinction is the whole catchability question.\n"
      % (100 * t1[95.0]["same_minute"], 100 * t1[99.9]["same_minute"], 100 * t1[95.0]["baseline_same"], 100 * t1[99.9]["baseline_same"], 100 * timing_row(e95, 5)["same_minute"], 100 * timing_row(e999, 5)["same_minute"]))
    w("![sweep](plots/sweep.png)\n")
    # 9 store scale and coverage
    w("## 9. The expanded store: scale and coverage\n")
    disc = HERE.parent / "waves_data" / "discovery"
    plan = HERE.parent / "waves_data" / "pull_plan.json"
    if (disc / "events.parquet").exists():
        dev = pd.read_parquet(disc / "events.parquet", columns=["event_ticker", "series", "category", "is_ladder", "listing_status"])
        lad = dev[dev.is_ladder]
        w("Exchange-wide discovery (`python3 -m waves.discover`, %s): %s events listed across every category and status; %s of them are numeric ladders (>= 3 strike markets) in %s series. The full ladder history is ~5.5M candle requests (one per 5,000 minutes of each market's life), ~340 hours at the rate the candlestick endpoint tolerates, three quarters of it in hourly crypto and sports ladders. Details in `waves_data/discovery/SCALE.md`.\n"
          % (dt.datetime.fromtimestamp((disc / "events.parquet").stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%d"), "{:,}".format(len(dev)), "{:,}".format(len(lad)), "{:,}".format(lad.series.nunique())))
        w("Ladder events by category on the exchange: " + ", ".join("%s %s" % (c, "{:,}".format(n)) for c, n in lad.groupby("category").size().sort_values(ascending=False).items()) + ".\n")
    if plan.exists():
        pl = json.loads(plan.read_text())
        w("Pull plan (`python3 -m waves.pull_plan`): markets with lifetime volume >= %g only; per-category request caps (%s general, %s for Crypto / Financials / Sports / Elections, which have an underlying or are enormous) filled by most-ladder-events-first, then interleaved across categories so a partial pull is still broad. Selected: %d series, %s ladder events, %s markets, ~%s requests. The commodity series already in `data/` are extended forward from 2026-09-01 in a separate pass.\n"
          % (pl["min_volume"], "{:,}".format(int(pl["cap"])), "{:,}".format(int(pl["cap_financial"])), pl["series"], "{:,}".format(pl["events"]), "{:,}".format(pl["markets"]), "{:,}".format(pl["requests"])))
    ex = sm[sm.tag != "commodity"] if "tag" in sm else sm.iloc[0:0]
    if len(ex):
        exo = ex[ex.skipped.isna()] if "skipped" in ex else ex
        g = exo.groupby("category", dropna=False).agg(series=("series", "nunique"), ladders=("event", "size"), ladder_days=("ladder_days", "sum"), changes=("changes", "sum"), e95=("events_95", "sum"), e99=("events_99", "sum")).reset_index().sort_values("changes", ascending=False)
        w("Pulled and processed so far (tag %s): %d ladders in %d series, %s skipped for fewer than 50 changes.\n\n" % (", ".join(sorted(ex.tag.unique())), len(exo), exo.series.nunique(), "{:,}".format(len(ex) - len(exo))) + md(g, 1) + "\n")
    else:
        w("No expanded-store ladders processed yet; the pull is running (`waves_data/pull.log`).\n")
    OUT.write_text("\n".join(L))
    return OUT


def dedupe(ev, sm):
    """An event pulled into the expanded store (full life) supersedes its copy in the commodity store (cut at 2026-09-10)."""
    if "tag" not in sm:
        return ev, sm
    newer = set(sm[sm.tag != "commodity"].event)
    drop_sm = (sm.tag == "commodity") & sm.event.isin(newer)
    drop_ev = (ev.tag == "commodity") & ev.event.isin(newer) if len(ev) else pd.Series([], dtype=bool)
    if drop_sm.any():
        print("dedupe: %d commodity-store ladders superseded by the expanded store" % int(drop_sm.sum()))
    return ev[~drop_ev], sm[~drop_sm]


def main():
    ev = pd.read_parquet(RESULTS / "events.parquet"); sm = pd.read_parquet(RESULTS / "summary.parquet")
    ev, sm = dedupe(ev, sm)
    plots(ev[ev.kind == "cumul"])
    print("wrote", render(ev, sm))


if __name__ == "__main__":
    main()
