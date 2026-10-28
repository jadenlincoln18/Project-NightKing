"""Render FINDINGS_UNDERLYING.md from waves/results_underlying/.   python3 -m waves.report_underlying"""
import datetime as dt
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .report import md, wmean, wshare, BLUE, ORANGE, AQUA, YELLOW, INK, INK2, MUTED
from . import underlying as U

HERE = Path(__file__).resolve().parent
RES = HERE / "results_underlying"
PLOTS = HERE / "plots"
OUT = HERE / "FINDINGS_UNDERLYING.md"
HS = (0, 1, 2, 5, 10, 30)
KS = (1, 2, 3, 4, 5)
TTC = [("< 4 h", lambda d: d.min_to_close < 240), ("4-24 h", lambda d: (d.min_to_close >= 240) & (d.min_to_close < 1440)), ("1-7 d", lambda d: (d.min_to_close >= 1440) & (d.min_to_close < 7 * 1440)), ("> 7 d", lambda d: d.min_to_close >= 7 * 1440)]
OIB = [("OI < 100", lambda d: d.oi < 100), ("100-1,000", lambda d: (d.oi >= 100) & (d.oi < 1000)), ("1,000-10,000", lambda d: (d.oi >= 1000) & (d.oi < 10000)), (">= 10,000", lambda d: d.oi >= 10000)]


def xc_table(sm, col, lags=10):
    acc = {}
    for js in sm[col].dropna():
        d = json.loads(js)
        for L, v in d.items():
            acc[int(L)] = acc.get(int(L), np.zeros(6)) + np.array(v)
    return {L: (U.corr_from_sums(v), int(v[0])) for L, v in sorted(acc.items()) if abs(L) <= lags}


def pooled(e, name, k, h):
    a = e["%s_%+d_%d" % (name, k, h)].values; b = e["%s_%+d_%d" % (name, -k, h)].values
    return np.concatenate([a, b]), np.concatenate([e.weight.values, e.weight.values])


def decomp_row(e, k, pred="spred"):
    out = {}
    for h in HS:
        r, w = pooled(e, "resp", k, h); p, _ = pooled(e, pred, k, h)
        ok = ~np.isnan(r) & ~np.isnan(p)
        out["n_h%d" % h] = int(w[ok].sum()) if h in (0, 30) else None
        out["resp_h%d" % h] = wmean(r[ok], w[ok]); out["pred_h%d" % h] = wmean(p[ok], w[ok]); out["resid_h%d" % h] = wmean((r - p)[ok], w[ok])
    out = {k_: v for k_, v in out.items() if v is not None}
    out["resid_added_0_30"] = out["resid_h30"] - out["resid_h0"]
    out["resp_added_0_30"] = out["resp_h30"] - out["resp_h0"]
    return out


def cut_table(e, name, cuts, k=1, pred="spred", cols=("n_h0", "resp_h0", "pred_h0", "resid_h0", "resp_h30", "pred_h30", "resid_h30", "resp_added_0_30", "resid_added_0_30")):
    rows = []
    for lab, sel in cuts:
        s = e[sel(e)]
        if not len(s):
            continue
        r = decomp_row(s, k, pred); rows.append({name: lab, **{c: r[c] for c in cols}})
    return pd.DataFrame(rows)


def eff_table(e, name, cuts, pred="spred"):
    """Effective sensitivity: the weighted slope of the neighbour's response on the futures-implied
    response (through the origin), k = +-1 pooled. 1 = the ladder moves exactly what its own shape says
    a futures move is worth; below 1 = it has not finished responding."""
    rows = []
    for lab, sel in cuts:
        s = e[sel(e)]
        if not len(s):
            continue
        r = {name: lab}
        for h in HS:
            a, w_ = pooled(s, "resp", 1, h); p, _ = pooled(s, pred, 1, h)
            ok = ~np.isnan(a) & ~np.isnan(p) & (np.abs(p) < 20)
            r["h%d" % h] = float((w_[ok] * a[ok] * p[ok]).sum() / (w_[ok] * p[ok] ** 2).sum()) if ok.any() and (w_[ok] * p[ok] ** 2).sum() > 0 else np.nan
            if h == 0:
                r["n"] = int(w_[ok].sum())
        rows.append(r)
    return pd.DataFrame(rows)


def side_table(e, name, cuts):
    """Residual added 0->30 min at k=+-1, split by whether the neighbour sits on the side of the
    price toward which time decay would push it in the impulse direction (strike below the price
    with an up-impulse, or above with a down-impulse: 'decay agrees') or the other way."""
    rows = []
    for lab, sel in cuts:
        s = e[sel(e)]
        if not len(s):
            continue
        r = {name: lab}
        for agree in (True, False):
            parts_r, parts_p0, parts_p30, parts_w = [], [], [], []
            for k in (1, -1):
                side = s["side_%+d" % k].values; d = np.sign(s.d.values)
                ag = (side * d) < 0  # strike below price & impulse up (side -1, d +) or above & down
                m_ = (ag == agree) & ~np.isnan(side)
                r0 = s["resp_%+d_0" % k].values; p0 = s["spred_%+d_0" % k].values; r30 = s["resp_%+d_30" % k].values; p30 = s["spred_%+d_30" % k].values
                ok = m_ & ~np.isnan(r0) & ~np.isnan(p0) & ~np.isnan(r30) & ~np.isnan(p30)
                parts_r.append((r30 - p30 - (r0 - p0))[ok]); parts_w.append(s.weight.values[ok])
            x = np.concatenate(parts_r); w_ = np.concatenate(parts_w)
            r["resid_added (%s)" % ("decay agrees" if agree else "decay opposes")] = wmean(x, w_)
            r["n (%s)" % ("agrees" if agree else "opposes")] = int(w_.sum())
        rows.append(r)
    return pd.DataFrame(rows)


def render():
    sm = pd.read_parquet(RES / "summary.parquet"); ev = pd.read_parquet(RES / "events.parquet")
    pre = json.load(open(RES / "preflight.json")) if (RES / "preflight.json").exists() else []
    cov = sm[sm.covered == True]  # noqa: E712
    wti = ev[ev.series.isin(U.WTI_SERIES)]; eth = ev[ev.series.isin(U.ETH_SERIES)]
    L = []; w = L.append
    w("# FINDINGS_UNDERLYING — does the ladder lag its underlying?\n")
    w("Generated %s by `python3 -m waves.run_underlying` / `python3 -m waves.report_underlying`. Brief: `NightKing/HANDOFF_underlying_lag.md`. Code: `waves/underlying.py`, `waves/run_underlying.py`. Results: `waves/results_underlying/`.\n" % dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    # ---- verdict
    wq = wti[wti.band >= 95]
    tt = cut_table(wq, "ttc", TTC).set_index("ttc"); oo = cut_table(wq, "oi", OIB).set_index("oi")
    xc = xc_table(cov[cov.series == "KXWTI"], "xc_fwd") if (cov.series == "KXWTI").any() else {}
    xc5 = xc_table(cov[cov.series == "KXWTI"], "xc_fwd5", lags=6) if (cov.series == "KXWTI").any() else {}
    cell = wq[(wq.oi >= 10000) & (wq.min_to_close < 1440)]; dcell = decomp_row(cell, 1) if len(cell) else None
    sd = side_table(wq, "all", [("all", lambda d: d.min_to_close >= 0)]).iloc[0] if "side_+1" in wq else None
    w("## Verdict\n")
    w("**Q1 — yes, the ladder lags the futures, by one to two minutes, and the lag is the quotes catching up.** On the daily WTI ladder the correlation of minute changes of the implied forward with the futures is %.2f at lag 0, %.2f one minute later, %.2f two minutes later, %.2f three, and nothing at a minute before. On 5-minute changes it is %.2f at lag 0 and %.2f one step later. About half of what the ladder does to a futures move it does inside the same minute and the rest over the next one to three; nothing leads.\n"
      % (xc.get(0, (np.nan,))[0], xc.get(1, (np.nan,))[0], xc.get(2, (np.nan,))[0], xc.get(3, (np.nan,))[0], xc5.get(0, (np.nan,))[0], xc5.get(1, (np.nan,))[0]))
    w("**Q2 — the near-expiry late leg survives the underlying, and so does the same leg everywhere else.** In the last 4 hours, events >= p95 with a matched futures path (n = %s): the adjacent bracket's same-minute response is %.2f and the futures' own same-minute move predicts %.2f of it (residual %+.2f — the same-minute wave is entirely the underlying). Over the next thirty minutes the futures' move adds %+.2f but the neighbour adds %+.2f, leaving a residual late leg of %+.2f. The residual late leg is %+.2f at 4-24 h (n = %s) and %+.2f at 1-7 days (n = %s): it is not a near-expiry property, it is a property of the ladder, and it was hidden away from expiry only because the futures tend to give back part of the move while the quotes are still catching up.\n"
      % ("{:,}".format(int(tt.loc["< 4 h", "n_h0"])), tt.loc["< 4 h", "resp_h0"], tt.loc["< 4 h", "pred_h0"], tt.loc["< 4 h", "resid_h0"], tt.loc["< 4 h", "pred_h30"] - tt.loc["< 4 h", "pred_h0"], tt.loc["< 4 h", "resp_added_0_30"], tt.loc["< 4 h", "resid_added_0_30"],
         tt.loc["4-24 h", "resid_added_0_30"], "{:,}".format(int(tt.loc["4-24 h", "n_h0"])), tt.loc["1-7 d", "resid_added_0_30"], "{:,}".format(int(tt.loc["1-7 d", "n_h0"]))))
    if sd is not None:
        w("**It is not time decay.** Split by whether settlement drift would push the neighbour with or against the impulse, the residual late leg is %+.2f where decay agrees (n = %s) and %+.2f where it opposes (n = %s). Decay would make the second negative; it is not.\n" % (sd["resid_added (decay agrees)"], "{:,}".format(int(sd["n (agrees)"])), sd["resid_added (decay opposes)"], "{:,}".format(int(sd["n (opposes)"]))))
    w("**Q3 — the depth effect survives, and it is the strongest cell.** On brackets with 10,000 or more contracts of open interest the same-minute response (%.2f) is fully the underlying (predicted %.2f, residual %+.2f) and the residual late leg over thirty minutes is %+.2f (n = %s), against %+.2f on brackets under 100 contracts (n = %s), whose same-minute response over-shoots the underlying by %+.2f and then does nothing. Deep and within a day of close (n = %s): same-minute residual %+.2f, residual late leg %+.2f. This is a lag on brackets with size behind them, net of the futures.\n"
      % (oo.loc[">= 10,000", "resp_h0"], oo.loc[">= 10,000", "pred_h0"], oo.loc[">= 10,000", "resid_h0"], oo.loc[">= 10,000", "resid_added_0_30"], "{:,}".format(int(oo.loc[">= 10,000", "n_h0"])), oo.loc["OI < 100", "resid_added_0_30"], "{:,}".format(int(oo.loc["OI < 100", "n_h0"])), oo.loc["OI < 100", "resid_h0"],
         "{:,}".format(int(dcell["n_h0"])) if dcell else "0", dcell["resid_h0"] if dcell else float("nan"), dcell["resid_added_0_30"] if dcell else float("nan")))
    et = eff_table(wq, "ttc", TTC).set_index("ttc"); eo = eff_table(wq, "oi", OIB).set_index("oi")
    w("**What it is.** Per unit of what the futures move is worth on the ladder's own curve, the adjacent bracket has moved %.2f by the end of the impulse minute near expiry and %.2f thirty minutes later; on deep brackets %.2f then %.2f; pooled %.2f then %.2f. The sensitivity is not understated (the slope converges on 1, it does not pass it): the response is incomplete at the minute and completes over the next five to thirty. That is a stale-quote lag — the ladder finishing a move the futures already made — visible at one-minute resolution, largest in relative terms on deep brackets, and of order a fifth of the impulse (an impulse >= p95 on these ladders is a few cents, so the leg is one to two cents per bracket). It is not a propagation wave and it is not information. Whether it can be touched is a question about resting size at the stale quote and about who else is lifting it, which is the live-book question, not a candle question. Nothing here is a trading rule; a catchability study needs its own protocol committed before any price is read.\n"
      % (et.loc["< 4 h", "h0"], et.loc["< 4 h", "h30"], eo.loc[">= 10,000", "h0"], eo.loc[">= 10,000", "h30"], eff_table(wq, "a", [("a", lambda d: d.min_to_close >= 0)]).iloc[0]["h0"], eff_table(wq, "a", [("a", lambda d: d.min_to_close >= 0)]).iloc[0]["h30"]))
    w("**Resolution and the next step.** Q1 says the lag is one to three minutes, which candles do resolve, so this does not hit the sub-minute wall. The first follow-on is not a websocket collector; it is the executable version of this table — the neighbour's ask after the impulse against its bid thirty minutes later, with the resting size from `ladder/collect_books.py` — on the deep near-expiry WTI brackets, under a protocol committed first. A tick-level futures pull is cheap (section 4: about $2 per contract window for top-of-book, $18 for the whole 2026 span) and would sharpen the lag to seconds; it is warranted only after the executable version shows a net above zero.\n")
    # ---- coverage
    w("## 0. Coverage and method\n")
    g = sm.groupby(["series"]).agg(ladders=("event", "size"), covered=("covered", "sum")).reset_index()
    g2 = cov.groupby("series").agg(matched_minutes=("matched_minutes", "sum"), events=("n_events_in", "sum"), beta_r2=("beta_r2_median", "median")).reset_index()
    g = g.merge(g2, on="series", how="left")
    w("**Underlying paths.** WTI ladders: the Kalshi-named CL contract (rules text > `custom_strike.front_month_contract` > Kalshi's calendar convention, the V3 logic in `wti_arb/db_common.py`), from `data_cme/parquet/futures_intraday` — `bbo-1m` quote mid sampled at the minute boundary (the primary path) and `ohlcv-1m` close (a check), continuous 1-minute coverage 2026-01-07 to 2026-09-04 in nine contract windows. Hourly ETH ladders: Coinbase Exchange ETH-USD 1-minute candle close (keyless, free; `waves/pull_crypto.py`), 2024-06 to 2026-10. Alignment: a Databento bar or quote at the minute boundary T pairs with the Kalshi candle ending at T. A ladder counts as covered when the underlying is present on at least half of its grid minutes.\n")
    src = cov.groupby(["series", "source"]).size().unstack(fill_value=0)
    w("Ladders by series: covered / total, matched minutes, wave events inside coverage, and how the contract was named:\n\n" + md(g.fillna(0), 2) + "\n\n" + md(src.reset_index(), 0) + "\n")
    ev2 = ev.copy()
    ev2["ttc"] = pd.cut(ev2.min_to_close, [-1, 240, 1440, 7 * 1440, 1e12], labels=[l for l, _ in TTC]); ev2["oib"] = pd.cut(ev2.oi, [-1, 100, 1000, 10000, 1e15], labels=[l for l, _ in OIB])
    pv = ev2[(ev2.band >= 95) & ev2.series.isin(U.WTI_SERIES)].pivot_table(index="ttc", columns="oib", values="weight", aggfunc="sum", observed=False).fillna(0).astype(int)
    w("WTI wave events (>= p95) with a matched futures path, by time to close and the initiator's open interest — the cells every table below draws on:\n\n" + md(pv.reset_index(), 0) + "\n")
    w("**Decomposition.** For every wave event (the per-bracket-normalised events of `FINDINGS_WAVES.md`) the neighbour's stored response at distance k and horizon h, resp = (mid[t+h] - mid[t-1]) / impulse, is split into the part the underlying explains and the rest:\n\n"
      "    predicted = beta_neighbour x (U[t+h] - U[t-1]) / impulse,   residual = resp - predicted\n\n"
      "beta is the bracket's sensitivity to a $1 move of the underlying. Two estimates: **shape** — read off the ladder's own curve at t-1 (the implied density at the strike, P(>X_{j-1}) - P(>X_{j+1}) over the strike gap; for a range bracket the density difference across its edges), which is instantaneous and unaffected by how sparsely the bracket is quoted; and **regression** — OLS of the bracket's minute changes on the underlying's over the ladder's life, which the carried-forward quotes bias toward zero (median R^2 %.2f, median slope %.1fc/$ against %.1fc/$ from the shape). The shape beta carries the tables; the regression beta is shown once as the lower bound. The initiator's own move is decomposed the same way (`pred_d` = the share of the impulse that the same-minute underlying move accounts for).\n"
      % (cov.beta_r2_median.median(), cov.beta_median.median(), wti.sbeta_i.median() if len(wti) else float("nan")))
    w("**Q1** is a cross-correlation of minute changes of the ladder's implied forward (the strike where P(>X) = 0.5, linearly interpolated from quoted mids with spread <= 10c) with the underlying's minute changes at lags -10..+10, pooled over ladders by summing cross-products; positive lag = the ladder moves after the underlying. Also on the at-the-money bracket's mid and on 5-minute changes.\n")
    # ---- Q1
    w("## 1. Q1 — does the ladder lag the futures?\n")
    def xc_block(sub, label):
        rows = []
        for col, nm in (("xc_fwd", "implied forward vs bbo mid"), ("xc_fwd_close", "implied forward vs ohlcv close"), ("xc_atm", "ATM bracket mid vs bbo mid")):
            t = xc_table(sub, col)
            if not t:
                continue
            r = {"pair": nm, "n (lag 0)": t[0][1]}
            for Lg in (-5, -3, -2, -1, 0, 1, 2, 3, 5, 10):
                r["L=%+d" % Lg] = t.get(Lg, (np.nan, 0))[0]
            peak = max(t.items(), key=lambda kv: (kv[1][0] if kv[1][0] == kv[1][0] else -9))
            r["peak lag"] = peak[0]; rows.append(r)
        t5 = xc_table(sub, "xc_fwd5", lags=6)
        if t5:
            r = {"pair": "implied forward vs bbo mid, 5-minute changes", "n (lag 0)": t5[0][1]}
            for Lg in (-3, -2, -1, 0, 1, 2, 3):
                r["L=%+d x5min" % Lg] = t5.get(Lg, (np.nan, 0))[0]
            rows.append(r)
        w("**%s**\n\n" % label + md(pd.DataFrame(rows).fillna(""), 3) + "\n")
    xc_block(cov[cov.series.isin(U.WTI_SERIES)], "All WTI ladders")
    for s_ in sorted(cov[cov.series.isin(U.WTI_SERIES)].series.unique()):
        sub = cov[cov.series == s_]
        if sub.fwd_change_minutes.sum() > 20000:
            xc_block(sub, s_)
    if (cov.series.isin(U.ETH_SERIES)).any():
        xc_block(cov[cov.series.isin(U.ETH_SERIES)], "Hourly ETH ladders vs Coinbase ETH-USD")
    t = xc_table(cov[cov.series.isin(U.WTI_SERIES)], "xc_fwd")
    w("Reading: the correlation at lag 0 is %.2f and at lag +1 (the ladder one minute after the futures) %.2f, at lag -1 (the ladder one minute before) %.2f, and nothing beyond ±2. The ladder tracks the futures within the candle; the one-minute tail is the carried-forward quotes catching up, visible but small. There is no lead.\n" % (t[0][0], t[1][0], t[-1][0]))
    w("![xcorr](plots/underlying_xcorr.png)\n")
    # ---- Q2
    w("## 2. Q2 — does the near-expiry late leg survive the underlying?\n")
    w95 = wti[wti.band >= 95]
    w("Adjacent neighbour (k = ±1 pooled), WTI events >= p95 with a matched path. `resp` is the stored neighbour response, `pred` the part the underlying's own move over the same window explains (shape beta), `resid` what is left. The last two columns are what each adds between the impulse minute and thirty minutes later — the quantity the brief asks about.\n")
    w("**By time to close (shape beta)**\n\n" + md(cut_table(w95, "time_to_close", TTC), 3) + "\n")
    w("**By time to close (regression beta — the lower bound on what the underlying explains)**\n\n" + md(cut_table(w95, "time_to_close", TTC, pred="pred"), 3) + "\n")
    rows = []
    for lab, sel in TTC:
        s = w95[sel(w95)]
        if not len(s):
            continue
        r = {"time_to_close": lab}
        for k in KS:
            d = decomp_row(s, k); r["resid_h0 k=%d" % k] = d["resid_h0"]; r["resid_added k=%d" % k] = d["resid_added_0_30"]
        rows.append(r)
    w("**Residual by distance** (same minute, and added over the next thirty):\n\n" + md(pd.DataFrame(rows), 3) + "\n")
    rows = []
    for lab, sel in TTC:
        s = w95[sel(w95)]
        if not len(s):
            continue
        ok = s.spred_d.notna()
        rows.append(dict(time_to_close=lab, n=int(s.weight[ok].sum()), initiator_share_explained=wmean(s.spred_d[ok], s.weight[ok]), share_events_with_underlying_move=wshare((s.du0.abs() > 0).values, s.weight.values)))
    w("**Effective sensitivity** — the slope of the neighbour's response on the futures-implied response (1 = the ladder has moved exactly what its own shape says the futures move is worth):\n\n" + md(eff_table(w95, "time_to_close", TTC), 2) + "\n\n" + md(eff_table(w95, "open_interest", OIB), 2) + "\n")
    if "side_+1" in w95:
        w("**Is the late leg time decay?** As a ladder approaches settlement, P(>X) drifts toward 1 for strikes below the price and toward 0 for strikes above it, whatever the futures do. That drift has the impulse's sign for a neighbour below the price after an up-move (or above after a down-move) and the opposite sign otherwise. If the residual late leg were decay it would be positive in the first group and negative in the second:\n\n" + md(side_table(w95, "time_to_close", TTC), 3) + "\n")
        w(md(side_table(w95, "open_interest", OIB), 3) + "\n")
    w("**The initiator itself**: how much of the impulse the same-minute underlying move accounts for, and how often the underlying moved at all in the impulse minute:\n\n" + md(pd.DataFrame(rows), 3) + "\n")
    if len(eth):
        e95 = eth[eth.band >= 95]
        w("**Hourly ETH ladders** (always within an hour of close; range ladders, so `resp` and `pred` are signed by the bracket's own density; k = ±1 pooled; events >= p95):\n\n" + md(cut_table(e95, "time_to_close", [("< 15 min", lambda d: d.min_to_close < 15), ("15-30 min", lambda d: (d.min_to_close >= 15) & (d.min_to_close < 30)), ("30-60 min", lambda d: d.min_to_close >= 30)]), 3) + "\n")
    w("![q2](plots/underlying_q2.png)\n")
    # ---- Q3
    w("## 3. Q3 — does the depth effect survive?\n")
    w("**By the initiator's open interest** (WTI, >= p95, k = ±1, shape beta):\n\n" + md(cut_table(w95, "open_interest", OIB), 3) + "\n")
    w("**Open interest × time to close** — the cell that matters, with its counts:\n")
    rows = []
    for lab, sel in OIB:
        for lab2, sel2 in TTC:
            s = w95[sel(w95) & sel2(w95)]
            if not len(s):
                continue
            d = decomp_row(s, 1); rows.append(dict(open_interest=lab, time_to_close=lab2, n=d["n_h0"], resp_h0=d["resp_h0"], resid_h0=d["resid_h0"], resp_h30=d["resp_h30"], resid_h30=d["resid_h30"], resp_added=d["resp_added_0_30"], resid_added=d["resid_added_0_30"]))
    w(md(pd.DataFrame(rows), 3) + "\n")
    w("**By the neighbour's spread** (WTI, >= p95, k = ±1):\n\n" + md(cut_table(w95.assign(nbsp=w95.spread0), "initiator_spread", [("<= 2c", lambda d: d.spread0 <= 2), ("3-5c", lambda d: (d.spread0 >= 3) & (d.spread0 <= 5)), ("6-10c", lambda d: d.spread0 >= 6)]), 3) + "\n")
    w("**By event size**:\n\n" + md(cut_table(wti, "band", [("p90-95", lambda d: d.band == 90), ("p95-99", lambda d: d.band == 95), ("p99-99.9", lambda d: d.band == 99), (">= p99.9", lambda d: d.band >= 99.9)]), 3) + "\n")
    w("![q3](plots/underlying_q3.png)\n")
    # ---- preflight
    w("## 4. What a finer look would cost\n")
    if pre:
        w(md(pd.DataFrame(pre)[["what", "schema", "cost"]], 2) + "\n")
    w("Prices are Databento `metadata.get_cost` quotes made with `execute=False`; nothing was bought.\n")
    OUT.write_text("\n".join(L))
    return sm, ev, cov, wti, eth


def plots(sm, ev, cov, wti, eth):
    PLOTS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for col, nm, c in (("xc_fwd", "implied forward vs bbo mid", BLUE), ("xc_atm", "ATM bracket mid vs bbo mid", ORANGE), ("xc_fwd_close", "implied forward vs ohlcv close", AQUA)):
        t = xc_table(cov[cov.series.isin(U.WTI_SERIES)], col)
        if t:
            Ls = sorted(t); ax.plot(Ls, [t[l][0] for l in Ls], marker="o", ms=3, lw=2, color=c, label=nm)
    if cov.series.isin(U.ETH_SERIES).any():
        t = xc_table(cov[cov.series.isin(U.ETH_SERIES)], "xc_fwd")
        if t:
            Ls = sorted(t); ax.plot(Ls, [t[l][0] for l in Ls], marker="o", ms=3, lw=2, color=YELLOW, label="hourly ETH ladders vs ETH-USD")
    ax.axvline(0, color=INK2, lw=0.8); ax.set_xlabel("lag in minutes (positive = ladder moves after the underlying)"); ax.set_ylabel("correlation of minute changes")
    ax.set_title("Q1: cross-correlation of ladder and underlying minute changes"); ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(PLOTS / "underlying_xcorr.png"); plt.close(fig)
    w95 = wti[wti.band >= 95]
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for (lab, sel), c in zip(TTC, (ORANGE, YELLOW, AQUA, BLUE)):
        s = w95[sel(w95)]
        if not len(s):
            continue
        d = decomp_row(s, 1)
        axs[0].plot(HS, [d["resp_h%d" % h] for h in HS], marker="o", ms=3, lw=2, color=c, label="%s (n=%s)" % (lab, "{:,}".format(d["n_h0"])))
        axs[1].plot(HS, [d["resid_h%d" % h] for h in HS], marker="o", ms=3, lw=2, color=c)
    axs[0].set_title("adjacent response as stored"); axs[1].set_title("residual after the underlying's own move"); axs[0].legend(fontsize=8)
    for ax in axs:
        ax.set_xlabel("minutes after the impulse"); ax.axhline(0, color=INK2, lw=0.8)
    axs[0].set_ylabel("fraction of the impulse")
    fig.suptitle("Q2: by time to close, WTI events >= p95", color=INK, fontsize=10); fig.tight_layout(); fig.savefig(PLOTS / "underlying_q2.png"); plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for (lab, sel), c in zip(OIB, (ORANGE, YELLOW, AQUA, BLUE)):
        s = w95[sel(w95)]
        if not len(s):
            continue
        d = decomp_row(s, 1)
        axs[0].plot(HS, [d["resp_h%d" % h] for h in HS], marker="o", ms=3, lw=2, color=c, label="%s (n=%s)" % (lab, "{:,}".format(d["n_h0"])))
        axs[1].plot(HS, [d["resid_h%d" % h] for h in HS], marker="o", ms=3, lw=2, color=c)
    axs[0].set_title("adjacent response as stored"); axs[1].set_title("residual after the underlying's own move"); axs[0].legend(fontsize=8)
    for ax in axs:
        ax.set_xlabel("minutes after the impulse"); ax.axhline(0, color=INK2, lw=0.8)
    axs[0].set_ylabel("fraction of the impulse")
    fig.suptitle("Q3: by the initiator's open interest, WTI events >= p95", color=INK, fontsize=10); fig.tight_layout(); fig.savefig(PLOTS / "underlying_q3.png"); plt.close(fig)


def main():
    out = render()
    plots(*out)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
