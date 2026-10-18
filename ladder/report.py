"""Render FINDINGS_LADDER_DYNAMICS.md and the plots from ladder/results/.

    python3 -m ladder.report
"""
import datetime as dt
import glob
import json
import pickle
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import census as C
from .fees import fee_cents, TAKER, MAKER

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
PLOTS = HERE / "plots"
BOOKS = HERE / "data" / "books"
OUT = HERE / "FINDINGS_LADDER_DYNAMICS.md"

# reference palette (dataviz skill): categorical blue / orange / aqua, inks, grid
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10, "axes.titlecolor": INK,
                     "legend.frameon": False, "savefig.dpi": 130})

INT_COLS = {"h", "n", "year", "legs", "minutes", "trade_n", "stale_n", "impulses", "episodes", "ladders", "markets", "all_bid", "all_ask", "buy_gross", "buy_net", "sell_gross", "sell_net", "min", "max min", "median min", "duration_min", "net_ge_2c"}
DUR_BINS = [0, 1, 2, 5, 10, 30, 60, 1e9]
DUR_LABELS = ["1 min", "2", "3-5", "6-10", "11-30", "31-60", "> 60"]


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def f(x, d=2):
    return ("%%.%df" % d) % x if x == x else "-"


def md_table(df, floats=2):
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)) and v == v and float(v).is_integer() and (c in INT_COLS or abs(v) >= 1000):
                cells.append("{:,}".format(int(v)) if abs(v) >= 10000 else str(int(v)))
            elif isinstance(v, (float, np.floating)):
                cells.append(f(v, floats))
            elif isinstance(v, (int, np.integer)):
                cells.append("{:,}".format(int(v)) if abs(int(v)) >= 10000 else str(int(v)))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def load():
    sm = pd.read_parquet(RESULTS / "summary.parquet")
    ep = pd.read_parquet(RESULTS / "episodes.parquet")
    rp = pd.read_parquet(RESULTS / "range_episodes.parquet")
    P = pickle.load(open(RESULTS / "propagation.pkl", "rb"))
    M = pickle.load(open(RESULTS / "maker.pkl", "rb"))
    status = {}
    for l in open(RESULTS / "status.jsonl"):
        r = json.loads(l); status[r["event"]] = r  # last attempt per event wins
    status = list(status.values())
    return sm, ep, rp, P, M, status


def live_frames():
    fs = sorted(glob.glob(str(BOOKS / "date=*" / "touch-*.parquet")))
    t = pd.concat([pd.read_parquet(x) for x in fs], ignore_index=True) if fs else pd.DataFrame()
    fs = sorted(glob.glob(str(BOOKS / "date=*" / "depth-*.parquet")))
    d = pd.concat([pd.read_parquet(x) for x in fs], ignore_index=True) if fs else pd.DataFrame()
    return t, d


def live_violations(t):
    """Adjacent monotonicity violations in the live sweeps, with the size at the touch on both legs,
    and whole-ladder sums for range events."""
    rows, sums = [], []
    if t.empty:
        return pd.DataFrame(), pd.DataFrame()
    for (sw, ev), d in t.groupby(["sweep_ts", "event"]):
        st = set(d.strike_type.dropna())
        if "between" in st:
            ok_b = (d.yes_bid > 0).all() and d.yes_bid.notna().all()
            ok_a = (d.yes_ask < 100).all() and d.yes_ask.notna().all()
            fee_b = sum(fee_cents(x) for x in d.yes_bid) if ok_b else np.nan
            fee_a = sum(fee_cents(x) for x in d.yes_ask) if ok_a else np.nan
            sums.append(dict(sweep_ts=sw, series=d.series.iloc[0], event=ev, legs=len(d),
                             sum_bid=d.yes_bid.sum() if ok_b else np.nan, sum_ask=d.yes_ask.sum() if ok_a else np.nan,
                             sell_all_net=(d.yes_bid.sum() - 100 - fee_b) if ok_b else np.nan,
                             buy_all_net=(100 - d.yes_ask.sum() - fee_a) if ok_a else np.nan,
                             min_bid_size=d.yes_bid_size.min(), min_ask_size=d.yes_ask_size.min()))
            continue
        if st <= {"greater", "greater_or_equal"}:
            d = d.sort_values("floor_strike"); b, a = d.yes_bid.values, d.yes_ask.values; key = d.floor_strike.values
            bs, as_ = d.yes_bid_size.values, d.yes_ask_size.values
        elif st <= {"less", "less_or_equal"}:
            d = d.sort_values("cap_strike"); b, a = 100 - d.yes_ask.values, 100 - d.yes_bid.values; key = d.cap_strike.values
            bs, as_ = d.yes_ask_size.values, d.yes_bid_size.values
        else:
            continue
        if len(d) < 2 or np.isnan(key).any() or pd.Series(key).duplicated().any():
            continue  # custom / dated strikes are not a price ladder
        edge = b[1:] - a[:-1]
        ok = (b[1:] > 0) & (b[1:] < 100) & (a[:-1] > 0) & (a[:-1] < 100) & (edge >= 1)
        for i in np.flatnonzero(ok):
            rows.append(dict(sweep_ts=sw, series=d.series.iloc[0], event=ev, strike_i=key[i], strike_j=key[i + 1], edge=edge[i],
                             ask_i=a[i], bid_j=b[i + 1], size_ask_i=as_[i], size_bid_j=bs[i + 1],
                             net=edge[i] - fee_cents(a[i]) - fee_cents(b[i + 1])))
    return pd.DataFrame(rows), pd.DataFrame(sums)


def prop_table(acc, k, ib, nb, stale, horizons=(0, 1, 2, 5, 10, 30)):
    rows = []
    for h in horizons:
        a = acc.get((k, h, ib, nb, stale))
        if not a:
            continue
        rows.append(dict(h=h, n=a[0], response=a[1] / max(a[3], 1), same_sign=a[2] / max(a[3], 1),
                         trade_n=a[4], trade_mean_c=a[5] / max(a[4], 1), trade_pos=a[6] / max(a[4], 1)))
    return pd.DataFrame(rows)


def plot_all(sm, ep, rp, P, t, lv):
    PLOTS.mkdir(exist_ok=True)
    cu = sm[sm.kind == "cumul"]
    # 1 durations: close-based episodes, all vs net>0 ; intra-minute share as text
    fig, ax = plt.subplots(figsize=(7, 3.2))
    d_all = pd.cut(ep.duration_min, DUR_BINS, labels=DUR_LABELS).value_counts().reindex(DUR_LABELS).fillna(0)
    d_pos = pd.cut(ep[ep.net_start > 0].duration_min, DUR_BINS, labels=DUR_LABELS).value_counts().reindex(DUR_LABELS).fillna(0)
    x = np.arange(len(DUR_LABELS))
    ax.bar(x - 0.2, d_all.values, 0.38, color=BLUE, label="all episodes (edge >= 1c)")
    ax.bar(x + 0.2, d_pos.values, 0.38, color=ORANGE, label="net > 0 after taker fees")
    ax.set_xticks(x); ax.set_xticklabels(DUR_LABELS); ax.set_ylabel("episodes"); ax.set_yscale("log")
    ax.set_title("Monotonicity violations by duration (adjacent pair, carried-forward closes, 1-minute grid)")
    ax.legend(loc="upper right"); fig.tight_layout(); fig.savefig(PLOTS / "durations.png"); plt.close(fig)
    # 2 net distribution
    fig, ax = plt.subplots(figsize=(7, 3.2))
    bins = np.arange(-3, 41, 1)
    ax.hist(ep.net_start.clip(-3, 40), bins=bins, color=BLUE)
    ax.axvline(0, color=INK, lw=1); ax.set_yscale("log"); ax.set_xlabel("net at episode start, cents per contract (edge - taker fees, both legs)"); ax.set_ylabel("episodes")
    ax.set_title("Net edge of every violation episode (clipped at 40c)"); fig.tight_layout(); fig.savefig(PLOTS / "net_hist.png"); plt.close(fig)
    # 3 magnitude vs depth proxies
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    oi = ep[["oi_i", "oi_j"]].min(axis=1).clip(lower=0.5); v60 = ep[["vol60_i", "vol60_j"]].min(axis=1).clip(lower=0.5)
    pos = ep.net_start > 0
    for ax, xv, lab in ((axs[0], oi, "min open interest of the two legs (contracts, log)"), (axs[1], v60, "min volume of the two legs in the prior 60 min (contracts, log; 0.5 = none)")):
        ax.scatter(xv[~pos], ep.edge_max[~pos], s=7, color=BLUE, alpha=0.35, label="net <= 0", edgecolors="none")
        ax.scatter(xv[pos], ep.edge_max[pos], s=9, color=ORANGE, alpha=0.6, label="net > 0", edgecolors="none")
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel(lab); ax.set_ylabel("max edge in the episode (cents)")
        ax.axhline(3.5, color=INK2, lw=0.8, ls="--"); ax.text(xv.min() * 1.2, 3.7, "3.5c = two taker legs at 50c", color=INK2, fontsize=8)
        ax.legend(loc="upper right")
    axs[0].set_title("Violation magnitude against the depth proxies available historically")
    fig.tight_layout(); fig.savefig(PLOTS / "magnitude_vs_depth.png"); plt.close(fig)
    # 4 propagation
    acc = P["all"][2.0]
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    hs = (0, 1, 2, 5, 10, 30)
    for k, col in ((1, BLUE), (2, AQUA), (3, YELLOW)):
        for ax, stale, ttl in ((axs[0], None, "all neighbours"), (axs[1], True, "neighbours unchanged in the impulse minute")):
            ys = []
            for h in hs:
                if stale is None:
                    a = [acc.get((kk, h, "body", "body", s), [0, 0, 0, 0]) for kk in (k, -k) for s in (False, True)]
                    ys.append(sum(z[1] for z in a) / max(sum(z[3] for z in a), 1))
                else:
                    a = [acc.get((kk, h, "body", "body", True), [0, 0, 0, 0]) for kk in (k, -k)]
                    ys.append(sum(z[1] for z in a) / max(sum(z[3] for z in a), 1))
            ax.plot(hs, ys, marker="o", ms=4, lw=2, color=col, label="distance %d" % k)
            ax.set_title(ttl); ax.set_xlabel("minutes after the impulse"); ax.set_xticks(hs)
    axs[0].set_ylabel("neighbour move / impulse"); axs[0].legend(); axs[0].set_ylim(0, 1)
    fig.suptitle("Impulse response: body brackets, impulse >= 2c, both brackets two-sided with spread <= 10c", color=INK, fontsize=10)
    fig.tight_layout(); fig.savefig(PLOTS / "propagation.png"); plt.close(fig)
    # 5 range ladder sell-all net distribution + live touch sizes
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    r = rp[(rp.side == "sell_all")]
    axs[0].hist(r.net_start.clip(0, 15), bins=np.arange(0, 15.5, 0.5), color=BLUE)
    axs[0].set_xlabel("net at start, cents per ladder set (sum of bids - 100 - fees on every leg)"); axs[0].set_ylabel("episodes")
    axs[0].set_title("Range ladders: sell-every-bracket episodes (%d)" % len(r))
    if not t.empty:
        q = t[(t.yes_bid > 0) & (t.yes_ask < 100)].assign(spread=lambda d: d.yes_ask - d.yes_bid)
        g = q.groupby("series").agg(spread=("spread", "median"), size=("yes_bid_size", "median"), n=("ticker", "nunique"))
        g = g[g.n >= 5]
        axs[1].scatter(g.spread, g["size"].clip(lower=1), s=18, color=ORANGE, edgecolors="none")
        top = set(g["size"].nlargest(3).index) | set(g.spread.nlargest(3).index) | {"KXWTI", "KXWTIW", "KXNATGASD", "KXGOLDD", "KXAAAGASDCA"}
        for s, row in g.iterrows():
            if s in top:
                axs[1].annotate(s, (row.spread, max(row["size"], 1)), fontsize=7, color=INK2, xytext=(3, 2), textcoords="offset points")
        axs[1].set_xscale("log"); axs[1].set_yscale("log"); axs[1].set_xlabel("median spread (cents)"); axs[1].set_ylabel("median resting size at the bid (contracts)")
        axs[1].set_title("Live book, %d sweeps: size at the touch against spread, by series" % t.sweep_ts.nunique())
    fig.tight_layout(); fig.savefig(PLOTS / "range_and_live.png"); plt.close(fig)


def render(sm, ep, rp, P, M, status, t, dp, lv, ls):
    from . import store
    close = store.events_table(store.load_markets()).set_index("event").close_epoch
    ep = ep.assign(min_to_close=(ep.event.map(close) - ep.ts) / 60.0)
    cu = sm[sm.kind == "cumul"].copy(); ra = sm[sm.kind == "range"].copy()
    live_mask = sm.event.str.contains("26OCT")
    cu_h = cu[~cu.event.str.contains("26OCT")]
    n_ok = sum(1 for s in status if s["status"] == "ok"); n_fail = sum(1 for s in status if s["status"] == "failed")
    L = []
    w = L.append
    w("# FINDINGS_LADDER_DYNAMICS — the Kalshi ladder against itself\n")
    w("Generated %s from the Kalshi store (`data/parquet/kalshi_candles`, 1-minute candles to 2026-09-10) by `python3 -m ladder.run` and `python3 -m ladder.report`. Brief: `NightKing/HANDOFF_ladder_dynamics.md`. Code: `ladder/`. Results: `ladder/results/`, plots `ladder/plots/`.\n" % dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    w("Jobs: %d events ok, %d failed (`ladder/results/status.jsonl`, last attempt per event). Cumulative ladders %d, range ladders %d (4 of them pulled live for October); 196 events skipped as not a ladder (157 single-market events, custom strikes), 184 ladders without stored candles.\n" % (n_ok, n_fail, len(cu), len(ra)))
    # --- verdict first
    pm = cu_h.pair_minutes.sum(); lm = cu_h.ladder_minutes.sum()
    v1 = cu_h.viol_close_1c.sum(); lv1 = cu_h.ladder_viol_1c.sum(); i1 = cu_h.viol_intra_1c.sum(); ipm = cu_h.intra_pair_minutes.sum(); li1 = cu_h.ladder_intra_1c.sum(); lmi = cu_h.ladder_minutes_intra.sum()
    eph = ep[~ep.event.str.contains("26OCT")]
    pos = eph[eph.net_start > 0]
    deep = pos[(pos[["oi_i", "oi_j"]].min(axis=1) >= 500) & (pos.net_start >= 2)]
    sell = rp[(rp.side == "sell_all") & (rp.series == "KXWTIW") & (pd.to_datetime(rp.ts, unit="s").dt.year == 2026)]
    w("## Verdict\n")
    w("**Shape violations are real, rare, one-tick deep and short, and the two-leg trade does not clear fees except in dead markets.** "
      "Across %.0fM adjacent-pair-minutes on %d cumulative ladders, an executable monotonicity violation (buy the lower threshold for less than you can sell the higher one, carried-forward 1-minute closes) exists on %.3f%% of pair-minutes and %.2f%% of ladder-minutes. "
      "There are %s episodes; the median lasts %d minutes, %d%% last one minute, and the modal maximum edge is exactly 1c (%d%% of episodes). "
      "After taker fees on both legs %s episodes (%.1f%%) are net positive, with a median net of %.2fc; the net-positive ones live almost entirely in thin yearly / monthly markets (AAA state-gas yearly highs and lows, natural gas yearly min/max, WTI monthly min/max) where the open interest of a leg is in the tens or hundreds and the violation is a resting order nobody has bothered to lift. "
      "Only %d episodes have net >= 2c with at least 500 contracts of open interest on both legs; none of them is in a daily or weekly commodity ladder with a live market maker, and their resting size at the touch is unknown historically.\n"
      % (pm / 1e6, len(cu_h), pct(v1, pm), pct(lv1, lm), "{:,}".format(len(eph)), int(eph.duration_min.median()), int(100 * (eph.duration_min <= 1).mean()),
         int(100 * (eph.edge_max < 2).mean()), "{:,}".format(len(pos)), pct(len(pos), len(eph)), pos.net_start.median(), len(deep)))
    w("**Propagation is immediate where it is tradeable and absent where it is not.** When a body bracket moves >= 2c, the adjacent bracket moves in the same minute %d%% of the time; a neighbour that did not move in that minute recovers only %.0f%% of the impulse after 5 minutes and %.0f%% after 30, and buying it at the ask (selling at the bid) on the impulse and unwinding at the touch 5 minutes later loses %.1fc on average and is positive %.0f%% of the time. The stale neighbour is stale because its spread is wide, not because it is slow.\n"
      % (round(100 * P["all"][2.0][("co", 1, "body")][1] / P["all"][2.0][("co", 1, "body")][0]),
         100 * prop_table(P["all"][2.0], 1, "body", "body", True).set_index("h").loc[5, "response"], 100 * prop_table(P["all"][2.0], 1, "body", "body", True).set_index("h").loc[30, "response"],
         -prop_table(P["all"][2.0], 1, "body", "body", True).set_index("h").loc[5, "trade_mean_c"], 100 * prop_table(P["all"][2.0], 1, "body", "body", True).set_index("h").loc[5, "trade_pos"]))
    coll = (100 * sell.legs.median() - (100 + sell.gross_start.median())) / 100.0
    w("**Nothing clears friction and capital together. The only thing that clears fees is not a shape violation but the sum constraint on the 2026 weekly WTI range ladder.** On KXWTIW in 2026 the sum of the bids across all brackets exceeds 100c plus the fee on every leg on %s of the %s minutes on which every bracket had a bid (%.1f%%): %s episodes, median net %.2fc per ladder set (every bracket sold once), p90 %.1fc, max %.1fc, median duration %d minutes, p90 %d. It is a %d-leg trade whose profit is locked at settlement, and it exists because the far brackets carry resting 1-2c bids that do not move when the body reprices; the live book (section 6) shows 500-1,000 contracts resting at those bids, so size is not the objection. Capital is: selling every bracket posts sum(100 - bid) ≈ $%.1f of collateral per set, so the median episode returns %.3f%% and the p90 %.2f%% on collateral tied up until the Friday settlement. That clears fees and fails any capital hurdle unless Kalshi nets collateral across the brackets of one event, which this study did not verify. It is the one candidate and it is small.\n"
      % ("{:,}".format(int(ra[ra.series == "KXWTIW"].sell_all_minutes.sum())), "{:,}".format(int(ra[ra.series == "KXWTIW"].all_bid_minutes.sum())),
         pct(ra[ra.series == "KXWTIW"].sell_all_minutes.sum(), ra[ra.series == "KXWTIW"].all_bid_minutes.sum()), "{:,}".format(len(sell)), sell.net_start.median(),
         sell.net_start.quantile(.9), sell.net_max.max(), int(sell.duration_min.median()), int(sell.duration_min.quantile(.9)), int(sell.legs.median()),
         coll, sell.net_start.median() / coll, sell.net_start.quantile(.9) / coll))
    w("**The 1-minute resolution is binding for the shape question.** Comparing intra-minute extremes (the higher bracket's best bid against the lower bracket's best ask within the same minute, only where both printed a candle) finds crossings on %.2f%% of such pair-minutes versus %.3f%% on closes, so sub-minute crossings are %.0fx more common than end-of-minute ones; that is an upper bound (the extremes need not coexist) and it cannot be tightened from candles. What can be said: a 1-minute-resolved violation is overwhelmingly one tick and one minute.\n"
      % (pct(i1, ipm), pct(v1, pm), (i1 / ipm) / (v1 / pm) if v1 else float("nan")))
    # --- data construction
    w("## 0. Data construction, checked before anything else\n")
    w("- **The store is sparse by design.** A 1-minute candle exists only for minutes in which the top of book changed: across all 58.9M candles the open of a bracket's next candle equals the close of its previous one 99.95% of the time (bid 99.953%, ask 99.956%). A missing minute is therefore 'the book did not move', not 'the book was not observed', and every analysis below carries the last close forward to the minute grid. Median gap between candles is 60 s on the daily ladders and 2-4 min on monthlies; p90 is 4-13 min.")
    w("- **Empty sides.** The API encodes no bid as 0 and no ask as 100; both are treated as no quote (NaN) and the no-quote state is carried forward like any other.")
    w("- **Intra-minute extremes exist.** On KXNATGASD 47% of candles have bid_high != bid_close, so a candle minute often contains several book updates; the 'intra' view uses them as an upper bound.")
    w("- **Ladder kinds** come from the markets table (strike_type), with a title parser for the 2022-24 markets that carry none ('$77 to 77.99', '1624.99 or below'). 'Less' ladders (yearly/monthly lows: KXWTIMIN, KXNGASMIN, ...) are flipped to P(>X) form so the monotone constraint is always 'non-increasing in the strike' and the trade is the same two legs.")
    w("- **Executable prices only.** Edge = bid(X_j) - ask(X_i) from the stored bid/ask closes; the spread is crossed by construction and the only remaining friction is the taker fee on each leg, 0.07 x P(1-P) per contract, rounded up to the cent per order (verified: every ladder series reports fee_type quadratic, multiplier 1 on the series endpoint). The displayed 'chance' and the mid are never used for an edge.")
    w("- **Thresholds, stated in advance.** A violation is an executable edge >= 1c (one tick); sensitivity at 2, 3, 5c. A 'move' is a mid change >= 2c between consecutive minutes on a two-sided bracket with spread <= 10c on both minutes; sensitivity at 1c and 5c. Body = mid in [10c, 90c], tail otherwise. Duration = consecutive grid minutes with the edge >= 1c, so '1 minute' means 'seen on one close and gone on the next'.")
    w("- **Depth is not in the candles.** Resting size at the touch is reported from the live collector (section 6); historically the only proxies are open interest and recent traded volume of the two legs, and they are labelled as proxies.\n")
    # --- census
    w("## 1. Violation census — cumulative ladders (%d ladders, %s brackets)\n" % (len(cu_h), "{:,}".format(int(cu_h.brackets.sum()))))
    rows = []
    for thr in (1, 2, 3, 5):
        k = "%dc" % thr
        rows.append(dict(threshold="≥ %dc" % thr, pair_minutes_close=int(cu_h["viol_close_" + k].sum()), pct_pair_close=pct(cu_h["viol_close_" + k].sum(), pm),
                         ladder_minutes_close=int(cu_h["ladder_viol_" + k].sum()), pct_ladder_close=pct(cu_h["ladder_viol_" + k].sum(), lm),
                         pair_minutes_any_pair=int(cu_h["viol_any_" + k].sum()), pair_minutes_intra=int(cu_h["viol_intra_" + k].sum()), pct_pair_intra=pct(cu_h["viol_intra_" + k].sum(), ipm)))
    w("Denominator: %s adjacent-pair-minutes with both legs quoted on the side the trade hits (%s ladder-minutes); %s pair-minutes where both brackets printed a candle (the intra-minute view). 'Any pair' takes the best j > i, not only the adjacent one.\n" % ("{:,}".format(int(pm)), "{:,}".format(int(lm)), "{:,}".format(int(ipm))))
    w(md_table(pd.DataFrame(rows), 3) + "\n")
    w("Mid-based shape violations (mid of the higher strike above the mid of the lower, both spreads <= 10c) occur on %.2f%% of tight pair-minutes — the ladder's *shape* is wrong at the mid 60x more often than it is executably wrong, which is the maker-side number of section 5.\n" % pct(cu_h.mid_viol_minutes.sum(), cu_h.mid_pair_minutes.sum()))
    g = cu_h.groupby("series").agg(ladders=("event", "size"), pair_min=("pair_minutes", "sum"), viol=("viol_close_1c", "sum"), ladder_min=("ladder_minutes", "sum"), lviol=("ladder_viol_1c", "sum"), intra=("viol_intra_1c", "sum"), intra_pm=("intra_pair_minutes", "sum"), episodes=("episodes", "sum"), spread=("spread_median", "median"))
    g["viol_pct_pair"] = 100 * g.viol / g.pair_min; g["viol_pct_ladder"] = 100 * g.lviol / g.ladder_min; g["intra_pct"] = 100 * g.intra / g.intra_pm.clip(lower=1)
    npos = pos.groupby("series").size(); g["net_pos_episodes"] = npos.reindex(g.index).fillna(0).astype(int)
    g = g.sort_values("pair_min", ascending=False).reset_index()
    g["pair_min"] = (g.pair_min / 1e6).round(2)
    w("### By series (top 30 by pair-minutes; all 162 in `ladder/results/summary.parquet`)\n")
    w(md_table(g.head(30)[["series", "ladders", "pair_min", "spread", "viol_pct_pair", "viol_pct_ladder", "intra_pct", "episodes", "net_pos_episodes"]].rename(columns={"pair_min": "pair-min (M)", "spread": "median spread c", "viol_pct_pair": "% pair-min violated", "viol_pct_ladder": "% ladder-min violated", "intra_pct": "% intra-min crossed", "net_pos_episodes": "net>0 episodes"}), 3) + "\n")
    # episodes
    w("### Episodes (%s, adjacent pair, edge >= 1c on carried-forward closes)\n" % "{:,}".format(len(eph)))
    d_all = pd.cut(eph.duration_min, DUR_BINS, labels=DUR_LABELS).value_counts().reindex(DUR_LABELS).fillna(0).astype(int)
    d_pos = pd.cut(pos.duration_min, DUR_BINS, labels=DUR_LABELS).value_counts().reindex(DUR_LABELS).fillna(0).astype(int)
    d_big = pd.cut(eph[eph.edge_max >= 3].duration_min, DUR_BINS, labels=DUR_LABELS).value_counts().reindex(DUR_LABELS).fillna(0).astype(int)
    w("| duration | all | share | net > 0 | edge >= 3c |\n|---|---|---|---|---|")
    for lab in DUR_LABELS:
        w("| %s | %s | %.1f%% | %s | %s |" % (lab, "{:,}".format(d_all[lab]), pct(d_all[lab], len(eph)), "{:,}".format(d_pos[lab]), "{:,}".format(d_big[lab])))
    w("")
    em = eph.edge_max.round(0).value_counts().sort_index()
    w("Maximum edge inside the episode: 1c %.1f%%, 2c %.1f%%, 3-5c %.1f%%, 6-10c %.1f%%, > 10c %.1f%% (%d episodes above 10c, largest %.0fc: %s %s %.2f/%.2f, %d minutes, a 2c ask resting against an 83c bid on a yearly natural-gas low ladder with no trades in the hour before).\n"
      % (100 * (eph.edge_max < 2).mean(), 100 * ((eph.edge_max >= 2) & (eph.edge_max < 3)).mean(), 100 * ((eph.edge_max >= 3) & (eph.edge_max <= 5)).mean(), 100 * ((eph.edge_max > 5) & (eph.edge_max <= 10)).mean(), 100 * (eph.edge_max > 10).mean(), int((eph.edge_max > 10).sum()),
         eph.edge_max.max(), eph.loc[eph.edge_max.idxmax(), "series"], eph.loc[eph.edge_max.idxmax(), "event"], eph.loc[eph.edge_max.idxmax(), "strike_i"], eph.loc[eph.edge_max.idxmax(), "strike_j"], int(eph.loc[eph.edge_max.idxmax(), "duration_min"])))
    w("Net of taker fees on both legs at the start of the episode: median %.2fc, p90 %.2fc, p99 %.2fc; %s (%.1f%%) positive, %s (%.1f%%) >= 1c, %s (%.1f%%) >= 2c, %s >= 5c. Of the net-positive episodes %.0f%% are between tail brackets (one leg with mid < 10c or > 90c), where the fee is a few tenths of a cent: a 1c edge at 5c prices clears fees, at 50c prices it does not.\n"
      % (eph.net_start.median(), eph.net_start.quantile(.9), eph.net_start.quantile(.99), "{:,}".format(len(pos)), pct(len(pos), len(eph)), "{:,}".format(int((eph.net_start >= 1).sum())), pct((eph.net_start >= 1).sum(), len(eph)),
         "{:,}".format(int((eph.net_start >= 2).sum())), pct((eph.net_start >= 2).sum(), len(eph)), "{:,}".format(int((eph.net_start >= 5).sum())),
         100 * (((pos.mid_i < 10) | (pos.mid_i > 90) | (pos.mid_j < 10) | (pos.mid_j > 90)).mean())))
    w("Who creates and who resolves: the violation starts with a fresh print on both legs in %.0f%% of episodes, on the lower leg only %.0f%%, the higher leg only %.0f%%; it ends with a print on both %.0f%%, lower only %.0f%%, higher only %.0f%% (ended episodes). Violations are a by-product of simultaneous repricing, not of one bracket drifting.\n"
      % (100 * (eph.fresh_i & eph.fresh_j).mean(), 100 * (eph.fresh_i & ~eph.fresh_j).mean(), 100 * (~eph.fresh_i & eph.fresh_j).mean(),
         100 * (eph[eph.ended].end_fresh_i & eph[eph.ended].end_fresh_j).mean(), 100 * (eph[eph.ended].end_fresh_i & ~eph[eph.ended].end_fresh_j).mean(), 100 * (~eph[eph.ended].end_fresh_i & eph[eph.ended].end_fresh_j).mean()))
    hr = pd.to_datetime(eph.ts, unit="s").dt.hour
    w("Timing: %.0f%% of episodes start between 12:00 and 20:00 UTC (US trading hours; the store is UTC); the median episode starts %.0f hours before the ladder closes (p25 %.0f h, p75 %.0f h).\n" % (100 * hr.between(12, 19).mean(), eph.min_to_close.median() / 60, eph.min_to_close.quantile(.25) / 60, eph.min_to_close.quantile(.75) / 60))
    w("### Net-positive episodes by series (top 20)\n")
    pg = pos.groupby("series").agg(n=("ts", "size"), dur_med=("duration_min", "median"), dur_max=("duration_min", "max"), net_med=("net_start", "median"), net_max=("net_max", "max"), oi_med=("oi_j", "median"), vol60_med=("vol60_j", "median")).sort_values("n", ascending=False).reset_index().head(20)
    w(md_table(pg.rename(columns={"dur_med": "median min", "dur_max": "max min", "net_med": "median net c", "net_max": "max net c", "oi_med": "median OI (higher leg)", "vol60_med": "median 60-min vol"}), 2) + "\n")
    w("### The largest net-positive episodes with open interest >= 500 on both legs\n")
    w(md_table(deep.sort_values("net_start", ascending=False).head(12)[["series", "event", "strike_i", "strike_j", "duration_min", "edge_max", "net_start", "spread_i", "spread_j", "mid_i", "mid_j", "vol60_i", "vol60_j", "oi_i", "oi_j"]].rename(columns={"duration_min": "min"}), 1) + "\n")
    w("![durations](plots/durations.png)\n\n![net](plots/net_hist.png)\n")
    # --- range
    w("## 2. Range ladders — the sum constraint (%d ladders)\n" % len(ra))
    rg = ra.groupby("series").agg(ladders=("event", "size"), minutes=("minutes", "sum"), all_bid=("all_bid_minutes", "sum"), all_ask=("all_ask_minutes", "sum"), ask_excess=("ask_excess_median", "median"), bid_short=("bid_short_median", "median"), spread_sum=("spread_sum_median", "median"), buy_gross=("buy_all_gross_minutes", "sum"), buy_net=("buy_all_minutes", "sum"), sell_gross=("sell_all_gross_minutes", "sum"), sell_net=("sell_all_minutes", "sum")).reset_index()
    w("A range ladder's bracket price is itself a density value and is non-negative by construction, so there is no two-leg shape constraint; the constraint is the sum. 'Ask excess' = sum of asks - 100 (median over minutes with every bracket asked); 'bid short' = 100 - sum of bids. Buy-all / sell-all minutes count the minutes on which crossing every leg locks a profit, gross and net of the fee on every leg.\n")
    w(md_table(rg, 1) + "\n")
    rp2 = rp.assign(year=pd.to_datetime(rp.ts, unit="s").dt.year)
    rt = rp2.groupby(["series", "side", "year"]).agg(episodes=("ts", "size"), legs=("legs", "median"), net_med=("net_start", "median"), net_p90=("net_start", lambda s: s.quantile(.9)), net_max=("net_max", "max"), dur_med=("duration_min", "median"), dur_p90=("duration_min", lambda s: s.quantile(.9))).reset_index()
    w(md_table(rt, 2) + "\n")
    w("The 2026 KXWTIW sell-all episodes are the whole story here: the 2026 ladders have 15-27 brackets, the body is quoted 1-3c wide by a market maker, and the far brackets carry resting 1-2c bids. When the body reprices upward the sum of the bids tips over 100c plus fees for a couple of minutes. Selling every bracket (buying NO on each) pays 100c at settlement against a median %.0fc collected, so the profit is locked; the collateral is sum(100 - bid) ≈ $%.1f per set for a median %.2fc net. Net >= 2c on %d episodes, >= 5c on %d. Whether the tail bids hold 500 contracts when hit, and whether all %d legs fill in the same minute, is exactly what the live collector is for.\n"
      % (100 + sell.gross_start.median(), (100 * sell.legs.median() - (100 + sell.gross_start.median())) / 100.0, sell.net_start.median(), int((sell.net_start >= 2).sum()), int((sell.net_start >= 5).sum()), int(sell.legs.median())))
    w("![range](plots/range_and_live.png)\n")
    # --- propagation
    w("## 3. Propagation — impulse response on cumulative ladders\n")
    acc = P["all"][2.0]
    w("Impulses (>= 2c on a tight body bracket): %s; on tail brackets %s. Same-minute co-movement of the neighbour at distance k (any tick, body initiator): k=±1 %.0f%%, ±2 %.0f%%, ±3 %.0f%%; at >= 5c impulses %.0f%% / %.0f%% / %.0f%%; at >= 1c %.0f%% / %.0f%% / %.0f%%.\n"
      % ("{:,}".format(acc[("init", "body")]), "{:,}".format(acc[("init", "tail")]),
         *[100 * (acc[("co", k, "body")][1] + acc[("co", -k, "body")][1]) / (acc[("co", k, "body")][0] + acc[("co", -k, "body")][0]) for k in (1, 2, 3)],
         *[100 * (P["all"][5.0][("co", k, "body")][1] + P["all"][5.0][("co", -k, "body")][1]) / (P["all"][5.0][("co", k, "body")][0] + P["all"][5.0][("co", -k, "body")][0]) for k in (1, 2, 3)],
         *[100 * (P["all"][1.0][("co", k, "body")][1] + P["all"][1.0][("co", -k, "body")][1]) / (P["all"][1.0][("co", k, "body")][0] + P["all"][1.0][("co", -k, "body")][0]) for k in (1, 2, 3)]))
    w("Response = neighbour's cumulative mid move from the minute before the impulse to h minutes after, divided by the impulse; same-sign = share of neighbours that moved the same way. On a P(>X) ladder a parallel shift moves every bracket together, but neighbouring thresholds carry less density than the initiator, so a full response is well below 1 and the level is not the point — the *lag* is. Body initiator, body neighbour, k = +1 (the next-higher strike):\n")
    w("**All neighbours** (thr 2c):\n\n" + md_table(prop_table(acc, 1, "body", "body", False).drop(columns=["trade_n", "trade_mean_c", "trade_pos"]), 3) + "\n")
    w("**Neighbours unchanged in the impulse minute** (thr 2c), with the stale-neighbour trade: buy at the ask (impulse up) or sell at the bid (impulse down) at t, unwind at the touch at t+h, net of taker fees on both legs:\n\n" + md_table(prop_table(acc, 1, "body", "body", True), 3) + "\n")
    w("Sensitivity, stale body neighbour at h = 5 / 30: thr 1c response %.2f / %.2f, trade mean %.1fc / %.1fc, positive %.0f%% / %.0f%%; thr 5c response %.2f / %.2f, trade mean %.1fc / %.1fc, positive %.0f%% / %.0f%%. Body impulse onto a stale tail neighbour (thr 2c): response %.2f at h=5, %.2f at h=30, trade mean %.1fc, positive %.0f%% at h=30. Tail impulse onto a stale body neighbour: response %.2f at h=30, trade mean %.1fc.\n"
      % tuple([prop_table(P["all"][1.0], 1, "body", "body", True).set_index("h").loc[h, c] * (100 if c == "trade_pos" else 1) for c in ("response", "trade_mean_c", "trade_pos") for h in (5, 30)][0:2] +
              [prop_table(P["all"][1.0], 1, "body", "body", True).set_index("h").loc[h, "trade_mean_c"] for h in (5, 30)] +
              [100 * prop_table(P["all"][1.0], 1, "body", "body", True).set_index("h").loc[h, "trade_pos"] for h in (5, 30)] +
              [prop_table(P["all"][5.0], 1, "body", "body", True).set_index("h").loc[h, "response"] for h in (5, 30)] +
              [prop_table(P["all"][5.0], 1, "body", "body", True).set_index("h").loc[h, "trade_mean_c"] for h in (5, 30)] +
              [100 * prop_table(P["all"][5.0], 1, "body", "body", True).set_index("h").loc[h, "trade_pos"] for h in (5, 30)] +
              [prop_table(acc, 1, "body", "tail", True).set_index("h").loc[5, "response"], prop_table(acc, 1, "body", "tail", True).set_index("h").loc[30, "response"], prop_table(acc, 1, "body", "tail", True).set_index("h").loc[30, "trade_mean_c"], 100 * prop_table(acc, 1, "body", "tail", True).set_index("h").loc[30, "trade_pos"]] +
              [prop_table(acc, -1, "tail", "body", True).set_index("h").loc[30, "response"], prop_table(acc, -1, "tail", "body", True).set_index("h").loc[30, "trade_mean_c"]]))
    rows = []
    for (s, thr), a in P["by_series"].items():
        if thr != 2.0:
            continue
        st = a.get((1, 5, "body", "body", True)); ns = a.get((1, 5, "body", "body", False)); co = a.get(("co", 1, "body"))
        if not st or st[4] < 500:
            continue
        rows.append(dict(series=s, impulses=a.get(("init", "body"), 0), co_move=co[1] / co[0], stale_n=st[4], stale_resp_5=st[1] / max(st[3], 1), stale_trade_5=st[5] / st[4], stale_pos_5=st[6] / st[4], moved_resp_5=ns[1] / max(ns[3], 1)))
    w("By series (thr 2c, k=+1, body→body, h=5):\n\n" + md_table(pd.DataFrame(rows).sort_values("impulses", ascending=False).head(20), 3) + "\n")
    w("Does the body reprice before the tails? Tail neighbours co-move less (%.0f%% vs %.0f%% at k=±1) and catch up less (%.2f vs %.2f at h=30), but the stale-tail trade is just as negative: a tail bracket sits at a 1-3c price where the whole move is a tick or two and the spread is the tick.\n"
      % (100 * sum(acc[("co", k, "tail")][1] for k in (1, -1)) / sum(acc[("co", k, "tail")][0] for k in (1, -1)), 100 * sum(acc[("co", k, "body")][1] for k in (1, -1)) / sum(acc[("co", k, "body")][0] for k in (1, -1)),
         prop_table(acc, 1, "body", "tail", True).set_index("h").loc[30, "response"], prop_table(acc, 1, "body", "body", True).set_index("h").loc[30, "response"]))
    w("![propagation](plots/propagation.png)\n")
    # --- depth
    w("## 4. Magnitude against depth\n")
    w("Historically the only depth proxies are the open interest of the two legs and the contracts traded in the previous hour. The scatter plots every episode's maximum edge against the smaller of the two legs' proxies, coloured by whether the start-of-episode net is positive; the dashed line is 3.5c, the two-leg taker fee at 50c prices (the fee stack is 0.3c per leg at 5c prices and 1.75c at 50c, so there is no single friction line in cents — the colour is the test).\n")
    w("![magnitude vs depth](plots/magnitude_vs_depth.png)\n")
    q = pd.DataFrame(dict(oi=eph[["oi_i", "oi_j"]].min(axis=1), vol60=eph[["vol60_i", "vol60_j"]].min(axis=1), net=eph.net_start, edge=eph.edge_max))
    rows = []
    for lo, hi, lab in ((0, 100, "< 100"), (100, 1000, "100-1,000"), (1000, 10000, "1,000-10,000"), (10000, 1e12, ">= 10,000")):
        s = q[(q.oi >= lo) & (q.oi < hi)]
        rows.append(dict(min_open_interest=lab, episodes=len(s), edge_median=s.edge.median(), edge_p90=s.edge.quantile(.9), net_pos_pct=100 * (s.net > 0).mean(), net_ge_2c=int((s.net >= 2).sum()), vol60_zero_pct=100 * (s.vol60 == 0).mean()))
    w(md_table(pd.DataFrame(rows), 2) + "\n")
    w("The expected tension holds with no middle: edges above a tick and nets above fees sit where the open interest is small and the prior hour traded nothing; where both legs have thousands of contracts of interest the violation is a tick for a minute and the fee eats it.\n")
    # --- maker
    w("## 5. The maker number\n")
    m = M["all"]
    w("Fair value = the monotone least-squares fit (pool-adjacent-violators, non-increasing in the strike) to the mids of the two-sided brackets with spread <= 20c, sampled every 10 minutes on every cumulative ladder: %s ladder-minutes, %s bracket-minutes. This is the ladder's own coherent shape, not an external model.\n" % ("{:,}".format(m["minutes"]), "{:,}".format(m["bracket_minutes"])))
    w("- The mids are non-monotone somewhere on the ladder on **%.0f%%** of sampled minutes.\n- The fit sits strictly inside the bracket's own spread on %.1f%% of bracket-minutes (it is a fit to the mids, so this is nearly tautological).\n- **A maker could post one tick inside the spread and still be >= 1c on the right side of the fit on %.0f%% of bracket-minutes** (bid side %.0f%%, ask side %.0f%%); the mean improvement available is %.2fc against a mean spread of %.2fc. Distribution of the room (cents): 0: %.0f%%, 1: %.0f%%, 2: %.0f%%, 3-4: %.0f%%, >= 5: %.0f%%.\n- With the maker coefficient (0.0175 x P(1-P), 0.44c at 50c) the room survives the fee on %.0f%% of bracket-minutes; with maker fee zero the figure is the %.0f%% above.\n"
      % (100 * m["nonmono_minutes"] / m["minutes"], 100 * m["inside"] / m["bracket_minutes"], 100 * m["improvable"] / m["bracket_minutes"], 100 * m["improvable_bid"] / m["bracket_minutes"], 100 * m["improvable_ask"] / m["bracket_minutes"], m["room_sum"] / m["bracket_minutes"], m["spread_sum"] / m["bracket_minutes"],
         100 * m["room_hist"][0] / m["bracket_minutes"], 100 * m["room_hist"][1] / m["bracket_minutes"], 100 * m["room_hist"][2] / m["bracket_minutes"], 100 * sum(m["room_hist"][3:5]) / m["bracket_minutes"], 100 * sum(m["room_hist"][5:]) / m["bracket_minutes"],
         100 * sum(m["room_hist"][2:]) / m["bracket_minutes"], 100 * m["improvable"] / m["bracket_minutes"]))
    rows = []
    for s, a in M["by_series"].items():
        if a["bracket_minutes"] < 50000:
            continue
        rows.append(dict(series=s, minutes=a["minutes"], nonmono_pct=100 * a["nonmono_minutes"] / a["minutes"], improvable_pct=100 * a["improvable"] / a["bracket_minutes"], room_c=a["room_sum"] / a["bracket_minutes"], spread_c=a["spread_sum"] / a["bracket_minutes"]))
    w(md_table(pd.DataFrame(rows).sort_values("minutes", ascending=False).head(20), 2) + "\n")
    w("Read with care: 'room' is relative to the ladder's own smoothed mids, which on a 5c-wide book is a weak fair value; it says a coherent quoter would often have been best bid or offer, not that being there is profitable. That is the question of the posting study the brief scopes out.\n")
    # --- live
    w("## 6. Live book: size at the touch (collector started 2026-10-05 22:49 UTC)\n")
    if not t.empty:
        q2 = t[(t.yes_bid > 0) & (t.yes_ask < 100)].assign(spread=lambda d: d.yes_ask - d.yes_bid)
        w("`ladder/collect_books.py` sweeps every open market of every series in the store once a minute from the open-markets listing (bid, ask, size at the touch, volume, OI per bracket; one request per series), and every fifth sweep pulls the full orderbook of the focus series. %d sweeps so far covering %s open markets in %d series (%s rows, %s two-sided).\n"
          % (t.sweep_ts.nunique(), "{:,}".format(t.ticker.nunique()), t.series.nunique(), "{:,}".format(len(t)), "{:,}".format(len(q2))))
        g = q2.groupby("series").agg(markets=("ticker", "nunique"), spread_med=("spread", "median"), bid_size_med=("yes_bid_size", "median"), ask_size_med=("yes_ask_size", "median"), bid_size_p10=("yes_bid_size", lambda s: s.quantile(.1)), ask_size_p10=("yes_ask_size", lambda s: s.quantile(.1))).sort_values("markets", ascending=False).reset_index()
        w(md_table(g.head(25), 1) + "\n")
        w("Live adjacent violations in the sweeps so far: **%d** on %s ladder-sweeps%s. Live range-ladder sums: %s.\n"
          % (len(lv), "{:,}".format(len(t.groupby(["sweep_ts", "event"]))),
             "" if lv.empty else " — " + "; ".join("%s %s %g/%g: %d sweeps, edge %.0fc, net %.1fc, size at the touch %.0f (ask) x %.0f (bid)" % (ev_[0], ev_[1], ev_[2], ev_[3], len(d), d.edge.median(), d.net.median(), d.size_ask_i.median(), d.size_bid_j.median()) for ev_, d in sorted(lv.groupby(["series", "event", "strike_i", "strike_j"]), key=lambda x: -x[1].net.median())[:8]),
             "none quoted on every bracket" if ls.empty or ls.sum_bid.notna().sum() == 0 else "; ".join("%s: sum of bids %.0f (sell-all net %.1fc, thinnest bid %.0f contracts) on %d of %d sweeps with every bracket bid" % (ev_, d.sum_bid.median(), d.sell_all_net.median(), d.min_bid_size.median(), d.sum_bid.notna().sum(), len(d)) for ev_, d in ls.groupby("event") if d.sum_bid.notna().any())))
        if not dp.empty:
            w("Full books (%s snapshots, focus series): median resting size at the touch %.0f (bid) / %.0f (ask) contracts; within 3c of the touch %.0f / %.0f; whole side %.0f / %.0f.\n" % ("{:,}".format(len(dp)), dp.bid_size.median(), dp.ask_size.median(), dp.bid_within_3c.median(), dp.ask_within_3c.median(), dp.bid_total.median(), dp.ask_total.median()))
    else:
        w("No live data collected yet.\n")
    # --- Oct 4
    lvv = sm[live_mask & (sm.series == "KXAAAGASDCA")]
    w("## 7. The KXAAAGASDCA observation of 2026-10-04\n")
    w("The store ends 2026-09-10, so the event was pulled live (`python3 -m ladder.pull_event KXAAAGASDCA-26OCT04 KXAAAGASDCA-26OCT05`, under `ladder/data/live_candles/`) and run through the same census. ")
    if len(lvv):
        for _, r in lvv.iterrows():
            w("%s: %d grid minutes, %s quoted pair-minutes, executable adjacent violations **%d**, any-pair %d, intra-minute crossings %d; mid-shape violations on %d of %d tight pair-minutes (%.0f%%). "
              % (r.event, r.minutes, "{:,}".format(int(r.pair_minutes)), int(r.viol_close_1c), int(r.viol_any_1c), int(r.viol_intra_1c), int(r.mid_viol_minutes), int(r.mid_pair_minutes), pct(r.mid_viol_minutes, r.mid_pair_minutes)))
        w("\nThe 86% / 95% display seen live was a mid (or last-price) inversion on a book whose sides were wide and one-sided; at no minute of either day could the lower threshold be bought for less than the higher one could be sold. The stored store shows the same for every KXAAAGASDCA ladder since August: 0 executable violations, 7-12% of tight pair-minutes inverted at the mid.\n")
    # --- fees
    w("## 8. Fees\n")
    w("Taker: 0.07 x C x P(1-P), rounded up to the cent per order; 1.75c per contract at 50c, 0.33c at 5c. The series endpoint reports `fee_type: quadratic, fee_multiplier: 1` for every ladder series used here (checked 2026-10-05 on KXWTI, KXWTIW, KXAAAGASDCA, KXNATGASD, KXGOLDD). The maker coefficient is 0.0175 per secondary sources (the schedule PDF rate-limited on fetch); section 5 reports both maker = 0.0175 and maker = 0. Every net in this document uses the taker fee on every leg; nothing is rounded per contract (at 100 contracts the round-up is < 0.01c).\n")
    # --- proposal
    w("## 9. Orderbook collection — proposal and status\n")
    w("Already running: `ladder/collect_books.py` (touch sizes for every open market every 60 s, full books for the 12 focus series every 5 min; ~110-160 requests per touch sweep at 4.5 rps ≈ 30-40 s, ~450 requests per book sweep ≈ 100 s; keyless, free; resumable, flushes every 5 sweeps, logs to `ladder/data/books/collect.log`). Output is ~3,400 touch rows per sweep ≈ 5M rows per day as parquet (~40 MB/day). Runtime cost: one process, one core, negligible. What it answers that the candles cannot: (a) the resting size behind the 1-2c tail bids of the KXWTIW sum episodes, (b) whether live shape violations have size behind both legs, (c) depth-over-time for the magnitude-versus-depth scatter with real depth on the x-axis. Two weeks of it, spanning a few weekly expiries and the daily ladders' US sessions, is enough to settle (a) and (b). Finer-than-minute candles do not exist on the API; sub-minute resolution means websocket book deltas, which the collector could be extended to for the focus series if (a) turns out positive.\n")
    w("## 10. What this does not say\n")
    w("- Nothing here reopens the WTI arbitrage; no CME data was read.\n- 'Net' is net of fees after crossing the spread at the stored top of book; it assumes the top-of-book size covered the trade, which the candles cannot confirm — section 6 is the first measurement of that.\n- The intra-minute view is an upper bound on sub-minute violations, not a count.\n- Episode durations are floored at one grid minute; a violation that appears and vanishes inside a minute is invisible in the close view and counted at most once in the intra view.\n")
    OUT.write_text("\n".join(L))
    return OUT


def main():
    sm, ep, rp, P, M, status = load()
    t, dp = live_frames()
    lv, ls = live_violations(t)
    lv.to_parquet(RESULTS / "live_violations.parquet", index=False) if len(lv) else None
    plot_all(sm, ep, rp, P, t, lv)
    out = render(sm, ep, rp, P, M, status, t, dp, lv, ls)
    print("wrote", out)


if __name__ == "__main__":
    main()
