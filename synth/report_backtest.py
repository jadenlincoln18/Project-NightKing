"""FINDINGS_BACKTEST.md from synth/results_backtest/runs_<series>.pkl: the gap distribution, Stage 18, the filter, P&L,
the denominator, the artifact checks and the mechanical verdict against BACKTEST_PROTOCOL.md §2.

    python3 -m synth.report_backtest
"""

from __future__ import annotations

import json
import pickle
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from . import backtest as bt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLOTS = HERE / "plots_backtest"

MONEY_BANDS = [("deep tail", 0.0, 0.05), ("moderate tail", 0.05, 0.20), ("body", 0.20, 0.80), ("favourite", 0.80, 1.01)]


def _f(x, fmt="%.2f") -> str:
    return "—" if x is None or (isinstance(x, float) and x != x) else fmt % x


def _pct(x) -> str:
    return "—" if x is None or (isinstance(x, float) and x != x) else "%.0f%%" % (100 * x)


def _c(x) -> str:   # probability -> cents
    return "—" if x is None or (isinstance(x, float) and x != x) else "%+.1f" % (100 * x)


def _git(args: List[str]) -> str:
    try:
        return subprocess.run(["git"] + args, cwd=str(ROOT), capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "—"


def load(series: str) -> List[Dict[str, Any]]:
    p = bt.runs_path(series)
    return pickle.load(open(p, "rb")) if p.exists() else []


def two_sided(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [b for b in r["brackets"] if b.get("kalshi_mid") is not None]


def cleared(rs: List[Dict[str, Any]], snap: str) -> List[Dict[str, Any]]:
    return [r for r in rs if r["snap"] == snap and r["outcome"] in ("cleared", "g4_split_half_fired", "sampler_fail")]


def tradeable_dates(rs: List[Dict[str, Any]], snap: str) -> List[Dict[str, Any]]:
    return [r for r in rs if r["snap"] == snap and r["outcome"] == "cleared"]


# --------------------------------------------------------------------------
# aggregates
# --------------------------------------------------------------------------

def denominator(rs: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rs:
        out[r["snap"]][r["outcome"]] += 1
    return {k: dict(v) for k, v in out.items()}


def bracket_status(rs: List[Dict[str, Any]], snap: str) -> Dict[str, int]:
    out: Dict[str, int] = defaultdict(int)
    for r in rs:
        if r["snap"] != snap:
            continue
        for b in r["brackets"]:
            out[b.get("status") or "unparsed"] += 1
    return dict(out)


def gap_by_moneyness(rs: List[Dict[str, Any]], snap: str) -> List[Dict[str, Any]]:
    rows = []
    bs = [b for r in cleared(rs, snap) for b in two_sided(r)]
    for name, lo, hi in MONEY_BANDS:
        sub = [b for b in bs if lo <= b["pq_mean"] < hi]
        if not sub:
            rows.append({"band": name, "n": 0})
            continue
        g = np.array([b["g"] for b in sub])
        gm = np.array([b["g_mid"] for b in sub])
        w = np.array([b["band90"] for b in sub])
        fr = np.array([b["friction"]["total"] for b in sub])
        rows.append({"band": name, "n": len(sub), "n_dates": len({(b.get("_date")) for b in sub}) if sub and "_date" in sub[0] else None,
                     "g_mean": float(g.mean()), "g_median": float(np.median(g)), "g_sd": float(g.std(ddof=1)) if len(g) > 1 else None,
                     "g_mid_mean": float(gm.mean()), "frac_pos": float(np.mean(g > 0)), "band_mean": float(w.mean()),
                     "friction_mean": float(np.nanmean(fr)), "frac_gt_band": float(np.mean(np.abs(g) > w)),
                     "frac_gt_band_friction": float(np.mean(np.abs(g) > w + np.where(np.isnan(fr), np.inf, fr))),
                     "kalshi_spread_mean": float(np.mean([b["kalshi_spread"] for b in sub])),
                     "pq_mean": float(np.mean([b["pq_mean"] for b in sub])), "pmkt_mean": float(np.mean([b["kalshi_mid"] for b in sub]))})
    return rows


def per_date(rs: List[Dict[str, Any]], snap: str) -> List[Dict[str, Any]]:
    rows = []
    for r in sorted(cleared(rs, snap), key=lambda r: r["settle_date"]):
        bs = two_sided(r)
        tails = [b for b in bs if b["pq_mean"] < 0.20]
        tr = [b for b in r["brackets"] if b.get("status") == "traded"]
        rows.append({"date": r["settle_date"], "outcome": r["outcome"], "n": len(bs), "g_mean": float(np.mean([b["g"] for b in bs])) if bs else None,
                     "g_tail_mean": float(np.mean([b["g"] for b in tails])) if tails else None,
                     "g_abs_mean": float(np.mean([abs(b["g"]) for b in bs])) if bs else None,
                     "band_mean": float(np.mean([b["band90"] for b in bs])) if bs else None,
                     "n_traded": len(tr), "n_interior": sum(1 for b in r["brackets"] if b.get("interior_minimum")),
                     "chi2": r.get("chi2_per_strike"), "meanF_minus_F0": r.get("meanF_minus_F0_cents"),
                     "stage18": r.get("stage18"), "F0": r.get("F0"), "settle": r.get("nymex_settle"),
                     "path_source": (r.get("real_path") or {}).get("source"), "n_bars": (r.get("real_path") or {}).get("n_bars")})
    return rows


def pooled_stage18(rs: List[Dict[str, Any]], snap: str) -> Optional[Dict[str, Any]]:
    blocks = []
    for r in tradeable_dates(rs, snap):
        ok = [b for b in two_sided(r) if bt.STAGE18_MID_MIN <= b["kalshi_mid"] <= bt.STAGE18_MID_MAX and b.get("mid_dollar") is not None and b.get("pq_draws") is not None]
        if len(ok) >= 2:
            blocks.append((np.array([b["kalshi_mid"] for b in ok]), np.stack([b["pq_draws"] for b in ok], axis=1).astype(float),
                           np.array([b["mid_dollar"] - r["F0"] for b in ok])))
    bc = bt.stage18_pooled(blocks)
    if bc is None:
        return None
    q = np.percentile(bc, [5, 50, 95], axis=0)
    return {"n_dates": len(blocks), "n_brackets": int(sum(len(b[0]) for b in blocks)),
            "b": q[:, 0].tolist(), "c": q[:, 1].tolist(),
            "b_below_1": bool(q[2, 0] < 1.0), "b_above_1": bool(q[0, 0] > 1.0), "c_excludes_0": bool(q[0, 1] > 0 or q[2, 1] < 0)}


def trades(rs: List[Dict[str, Any]], snap: str) -> List[Dict[str, Any]]:
    out = []
    for r in sorted(tradeable_dates(rs, snap), key=lambda r: r["settle_date"]):
        for b in r["brackets"]:
            if b.get("status") == "traded":
                out.append(dict(b, _date=r["settle_date"], _month=r["settle_date"][:7]))
    return out


def pnl_summary(tr: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not tr:
        return {"n": 0}
    pnl = np.array([t["pnl_per_contract"] if t.get("pnl_per_contract") is not None else np.nan for t in tr])
    ok = ~np.isnan(pnl)
    by_date: Dict[str, float] = defaultdict(float)
    for t, p in zip(tr, pnl):
        if p == p:
            by_date[t["_date"]] += p
    dates_pnl = np.array(sorted(by_date.values(), reverse=True))
    return {"n": len(tr), "n_with_pnl": int(ok.sum()), "n_dates": len(by_date), "months": sorted({t["_month"] for t in tr}),
            "pnl_per_contract_mean": float(pnl[ok].mean()) if ok.any() else None, "pnl_total_per_contract": float(pnl[ok].sum()) if ok.any() else None,
            "pnl_at_500": float(pnl[ok].sum() * bt.SIZE_APPLICABLE) if ok.any() else None, "pnl_at_50": float(pnl[ok].sum() * bt.SIZE_DEPTH_CLEARED) if ok.any() else None,
            "frac_dates_positive": float(np.mean(dates_pnl > 0)) if len(dates_pnl) else None,
            "pnl_without_best3_per_contract": float(dates_pnl[3:].sum()) if len(dates_pnl) > 3 else (0.0 if len(dates_pnl) else None),
            "frac_in_ramp": float(np.mean([bool(t.get("in_ramp")) for t in tr])), "ramp_prob_mean": float(np.nanmean([t.get("ramp_prob", np.nan) for t in tr])),
            "locked_gap_mean": float(np.nanmean([t.get("locked_gap", np.nan) for t in tr])),
            "n_loo_near_edge": sum(1 for t in tr if t.get("loo_near_edge")),
            "pnl_loo_near_edge": float(np.nansum([t["pnl_per_contract"] for t in tr if t.get("loo_near_edge") and t.get("pnl_per_contract") is not None])) if any(t.get("loo_near_edge") for t in tr) else None,
            "sides": {s: sum(1 for t in tr if t["side"] == s) for s in ("buy_kalshi", "sell_kalshi")},
            "by_date": dict(by_date)}


def verdict(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
    lead, other = bt.LEAD_SNAP, [s for s in bt.SNAPS if s != bt.LEAD_SNAP][0]
    p_lead, p_other = pooled_stage18(rs, lead), pooled_stage18(rs, other)
    b1 = False
    b1_reason = "pooled Stage 18 unavailable"
    if p_lead and p_other:
        same_b = (p_lead["b_below_1"] and p_other["b_below_1"]) or (p_lead["b_above_1"] and p_other["b_above_1"])
        same_c = p_lead["c_excludes_0"] and p_other["c_excludes_0"] and np.sign(p_lead["c"][1]) == np.sign(p_other["c"][1])
        b1 = bool(same_b or same_c)
        b1_reason = "b 90%% CI %s at %s, %s at %s; c 90%% CI %s at %s, %s at %s" % (
            "[%.2f, %.2f]" % (p_lead["b"][0], p_lead["b"][2]), lead, "[%.2f, %.2f]" % (p_other["b"][0], p_other["b"][2]), other,
            "[%.3f, %.3f]" % (p_lead["c"][0], p_lead["c"][2]), lead, "[%.3f, %.3f]" % (p_other["c"][0], p_other["c"][2]), other)
    tr = trades(rs, lead)
    dates = {t["_date"] for t in tr}
    months = {t["_month"] for t in tr}
    direction = None
    if p_lead and p_lead["b_below_1"]:
        direction = "longshots rich"
    elif p_lead and p_lead["b_above_1"]:
        direction = "longshots cheap"
    agree = None
    if tr and direction:
        # longshots rich <=> g > 0 on brackets with pq < 0.5, g < 0 on favourites
        exp_sign = np.array([(+1 if t["pq_mean"] < 0.5 else -1) * (1 if direction == "longshots rich" else -1) for t in tr])
        agree = float(np.mean(np.sign([t["g"] for t in tr]) == exp_sign))
    elif tr and p_lead and p_lead["c_excludes_0"]:
        exp_sign = np.sign(p_lead["c"][1]) * np.sign([(t["mid_dollar"] or 0) - 0 for t in tr])
        agree = float(np.mean(np.sign([t["g"] for t in tr]) == exp_sign))
    b2 = bool(len(dates) >= 8 and len(months) >= 3 and agree is not None and agree >= 0.75)
    ps = pnl_summary(tr)
    b3 = bool(ps.get("n_with_pnl") and ps["pnl_total_per_contract"] > 0 and ps["frac_dates_positive"] >= 0.60 and ps["pnl_without_best3_per_contract"] > 0)
    word = "EDGE" if (b1 and b2 and b3) else ("STRUCTURE, NOT AN EDGE" if b1 else "NULL")
    return {"B1": b1, "B1_reason": b1_reason, "B2": b2, "B2_detail": {"n_dates": len(dates), "n_months": len(months), "sign_agreement": agree, "direction": direction},
            "B3": b3, "B3_detail": {k: ps.get(k) for k in ("n", "pnl_total_per_contract", "frac_dates_positive", "pnl_without_best3_per_contract")},
            "verdict": word, "pooled": {lead: p_lead, other: p_other}}


# --------------------------------------------------------------------------
# artifact checks
# --------------------------------------------------------------------------

def artifact_checks(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    lead, other = bt.LEAD_SNAP, [s for s in bt.SNAPS if s != bt.LEAD_SNAP][0]
    pd_ = per_date(rs, lead)
    x = np.array([r["meanF_minus_F0"] for r in pd_ if r["g_mean"] is not None and r["meanF_minus_F0"] is not None])
    y = np.array([r["g_mean"] for r in pd_ if r["g_mean"] is not None and r["meanF_minus_F0"] is not None])
    out["corr_gap_vs_forward_error"] = float(np.corrcoef(x, y)[0, 1]) if len(x) > 3 else None
    out["forward_error_cents_median_abs"] = float(np.median(np.abs(x))) if len(x) else None
    # same bracket at both snapshots
    by = {(r["settle_date"], b["ticker"]): b for r in cleared(rs, lead) for b in two_sided(r)}
    pairs = [(by[(r["settle_date"], b["ticker"])]["g"], b["g"]) for r in cleared(rs, other) for b in two_sided(r) if (r["settle_date"], b["ticker"]) in by]
    if pairs:
        a = np.array(pairs)
        out["pairs"] = len(pairs)
        out["sign_agreement_snapshots"] = float(np.mean(np.sign(a[:, 0]) == np.sign(a[:, 1])))
        out["corr_snapshots"] = float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]) if len(pairs) > 3 else None
    # chain's own digital vs the extractor vs Kalshi
    bs = [b for r in cleared(rs, lead) for b in two_sided(r) if b.get("chain_digital_mid") is not None]
    if bs:
        cd = np.array([b["chain_digital_mid"] for b in bs])
        pq = np.array([b["pq_mean"] for b in bs])
        km = np.array([b["kalshi_mid"] for b in bs])
        out["chain_digital"] = {"n": len(bs), "mean_abs_chain_minus_pq_cents": float(100 * np.mean(np.abs(cd - pq))),
                                "mean_kalshi_minus_chain_cents": float(100 * np.mean(km - cd)), "mean_kalshi_minus_pq_cents": float(100 * np.mean(km - pq)),
                                "frac_same_sign": float(np.mean(np.sign(km - cd) == np.sign(km - pq)))}
    out["path_sources"] = {s: dict(zip(*np.unique([r["path_source"] or "none" for r in per_date(rs, s)], return_counts=True))) for s in bt.SNAPS}
    return out


# --------------------------------------------------------------------------
# plots
# --------------------------------------------------------------------------

def plots(rs: List[Dict[str, Any]], series: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    PLOTS.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, snap in zip(axes, bt.SNAPS):
        bs = [b for r in cleared(rs, snap) for b in two_sided(r)]
        if not bs:
            continue
        pq = np.array([b["pq_mean"] for b in bs])
        g = np.array([b["g"] for b in bs])
        w = np.array([b["band90"] for b in bs])
        tr = np.array([b["status"] == "traded" for b in bs])
        ax.errorbar(100 * pq, 100 * g, yerr=50 * w, fmt=".", alpha=0.35, color="grey", label="band 90%")
        ax.scatter(100 * pq[tr], 100 * g[tr], color="red", s=18, zorder=3, label="cleared filter")
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xscale("symlog", linthresh=5)
        ax.set_xlabel("Act III bracket probability (¢)")
        ax.set_ylabel("gap: Kalshi executable − Act III (¢)")
        ax.set_title("%s %s" % (series, snap))
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS / ("gap_by_moneyness_%s.png" % series), dpi=110)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(12, 4))
    for snap, col in zip(bt.SNAPS, ("tab:blue", "tab:orange")):
        rows = per_date(rs, snap)
        ds = [r["date"] for r in rows if r["g_tail_mean"] is not None]
        ax.plot(ds, [100 * r["g_tail_mean"] for r in rows if r["g_tail_mean"] is not None], "o-", color=col, label="%s mean tail gap (pq < 20¢)" % snap)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("¢")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(PLOTS / ("tail_gap_by_date_%s.png" % series), dpi=110)
    plt.close(fig)


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def render_series(rs: List[Dict[str, Any]], series: str, lead_section: bool) -> List[str]:
    L: List[str] = []
    den = denominator(rs)
    L.append("### Denominator — %s" % series)
    L.append("| outcome | " + " | ".join(bt.SNAPS) + " |\n|---|" + "---|" * len(bt.SNAPS))
    outcomes = ["cleared", "g4_split_half_fired", "sampler_fail", "g0a_no_same_day_expiry", "g0b_contract_mismatch", "g0c_too_few_strikes",
                "g0d_no_intraday_bars", "no_kalshi_candles", "no_kalshi_event", "extraction_error"]
    for o in outcomes:
        L.append("| %s | %s |" % (o, " | ".join(str(den.get(s, {}).get(o, 0)) for s in bt.SNAPS)))
    L.append("| **total dates** | %s |" % " | ".join(str(sum(den.get(s, {}).values())) for s in bt.SNAPS))
    L.append("")
    L.append("Bracket statuses (every bracket of every date that reached the comparison):\n")
    L.append("| status | " + " | ".join(bt.SNAPS) + " |\n|---|" + "---|" * len(bt.SNAPS))
    sts = ["traded", "below_threshold", "no_two_sided_kalshi_quote", "date_gated", "price_out_of_range", "band_too_wide", "interior_minimum", "cme_leg_unquoted"]
    bstat = {s: bracket_status(rs, s) for s in bt.SNAPS}
    for st in sts:
        L.append("| %s | %s |" % (st, " | ".join(str(bstat[s].get(st, 0)) for s in bt.SNAPS)))
    L.append("")
    for snap in bt.SNAPS:
        L.append("### Gap by moneyness — %s %s%s" % (series, snap, " (lead)" if snap == bt.LEAD_SNAP else ""))
        L.append("Brackets with a two-sided Kalshi quote on dates that reached the comparison (gated dates included, marked in the per-date table). "
                 "Gap = executable Kalshi price on the side the trade would hit − Act III posterior mean, in cents of probability; band = 90% posterior width; "
                 "friction per BACKTEST_PROTOCOL §4 with measured CME half-spreads.\n")
        L.append("| band (Act III prob) | n | mean Kalshi | mean Act III | mean gap | median gap | sd | gap > 0 | mean band | mean friction | \\|gap\\| > band | \\|gap\\| > band + friction | Kalshi spread |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in gap_by_moneyness(rs, snap):
            if row["n"] == 0:
                L.append("| %s | 0 | | | | | | | | | | | |" % row["band"])
                continue
            L.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                row["band"], row["n"], _c(row["pmkt_mean"]).replace("+", ""), _c(row["pq_mean"]).replace("+", ""), _c(row["g_mean"]), _c(row["g_median"]),
                _f(100 * row["g_sd"], "%.1f") if row["g_sd"] is not None else "—", _pct(row["frac_pos"]), _f(100 * row["band_mean"], "%.1f"),
                _f(100 * row["friction_mean"], "%.1f"), _pct(row["frac_gt_band"]), _pct(row["frac_gt_band_friction"]), _f(100 * row["kalshi_spread_mean"], "%.1f")))
        L.append("")
    L.append("### Per date — %s" % series)
    L.append("| date | snap | outcome | n two-sided | mean gap | mean tail gap (pq<20¢) | mean \\|gap\\| | mean band | traded | interior-min removed | χ²/strike | E[F]−F₀ (¢) | path | Stage 18 b [5,50,95] | c |")
    L.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|")
    for snap in bt.SNAPS:
        for r in per_date(rs, snap):
            s18 = r["stage18"]
            L.append("| %s | %s | %s | %d | %s | %s | %s | %s | %d | %d | %s | %s | %s | %s | %s |" % (
                r["date"], snap, r["outcome"].replace("g4_split_half_fired", "**split-half fired**").replace("sampler_fail", "**sampler**"), r["n"],
                _c(r["g_mean"]), _c(r["g_tail_mean"]), _f(100 * r["g_abs_mean"], "%.1f") if r["g_abs_mean"] is not None else "—",
                _f(100 * r["band_mean"], "%.1f") if r["band_mean"] is not None else "—", r["n_traded"], r["n_interior"], _f(r["chi2"]),
                _f(r["meanF_minus_F0"], "%+.1f"), r["path_source"] or "—",
                ("%.2f [%.2f, %.2f]" % (s18["q50"][1], s18["q05"][1], s18["q95"][1])) if s18 else "—",
                ("%.3f [%.3f, %.3f]" % (s18["q50"][2], s18["q05"][2], s18["q95"][2])) if s18 else "—"))
    L.append("")
    L.append("### Stage 18, pooled — %s" % series)
    L.append("Per posterior draw, logit(Kalshi mid) = a_date + b·logit(p^Q) + c·(bracket midpoint − F₀, $); brackets with a two-sided quote and mid in [1¢, 99¢]; p^Q clipped at 10⁻³. "
             "b < 1 is the favourite–longshot bias, c ≠ 0 the state tilt.\n")
    L.append("| snapshot | dates | brackets | b [5, 50, 95%] | b CI below 1 | c [5, 50, 95%] | c CI excludes 0 |\n|---|---:|---:|---|---|---|---|")
    for snap in bt.SNAPS:
        p = pooled_stage18(rs, snap)
        if p is None:
            L.append("| %s | — | — | — | — | — | — |" % snap)
        else:
            L.append("| %s | %d | %d | %.2f [%.2f, %.2f] | %s | %.3f [%.3f, %.3f] | %s |" % (snap, p["n_dates"], p["n_brackets"], p["b"][1], p["b"][0], p["b"][2],
                                                                                          "yes" if p["b_below_1"] else ("**above 1**" if p["b_above_1"] else "no"),
                                                                                          p["c"][1], p["c"][0], p["c"][2], "yes" if p["c_excludes_0"] else "no"))
    L.append("")
    for snap in bt.SNAPS:
        tr = trades(rs, snap)
        ps = pnl_summary(tr)
        L.append("### Stage 19 — brackets clearing the filter, %s %s" % (series, snap))
        if not tr:
            L.append("None.\n")
            continue
        L.append("| date | bracket | side | Kalshi exec | Act III | band | gap | friction (K fee / CME spread / CME fees) | excess | LOO near edge | settled | locked gap | realised P&L / contract | in ramp | P(ramp) |")
        L.append("|---|---|---|---:|---:|---:|---:|---|---:|---|---|---:|---:|---|---:|")
        for t in tr:
            fr = t["friction"]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s (%s / %s / %s) | %s | %s | %s | %s | %s | %s | %s |" % (
                t["_date"], t["sub_title"], t["side"].replace("_kalshi", " Kalshi"), _f(100 * t["P_exec"], "%.0f¢"), _f(100 * t["pq_mean"], "%.1f¢"), _f(100 * t["band90"], "%.1f"),
                _c(t["g"]), _f(100 * fr["total"], "%.1f"), _f(100 * fr["kalshi_fee"], "%.1f"), _f(100 * fr["cme_spread"], "%.1f"), _f(100 * fr["cme_fees"], "%.1f"),
                _f(100 * t["excess"], "%.1f"), "yes" if t["loo_near_edge"] else "", "yes" if t.get("settled_yes") else "no",
                _c(t.get("locked_gap")), _c(t.get("pnl_per_contract")), "**yes**" if t.get("in_ramp") else "", _pct(t.get("ramp_prob"))))
        L.append("")
        L.append("Dates: %d (%s); months: %s. Sides: %s. Realised P&L, held to settlement, net of the full stack: **%s¢ per contract summed over %d trades** "
                 "(mean %s¢); at the applicable 500 contracts per structure **$%s**, at the 50 the depth scan cleared $%s (not available on weekly dates). "
                 "Dates with positive P&L: %s. Without the three best dates: %s¢. Settlement landed in a ramp on %s of trades (posterior P(ramp) mean %s). "
                 "Trades with a LOO-flagged strike within $1 of an edge: %d%s.\n" % (
                     ps["n_dates"], ", ".join(sorted(ps["by_date"])), ", ".join(ps["months"]), ps["sides"], _c(ps["pnl_total_per_contract"]).replace("+", ""), ps["n"],
                     _c(ps["pnl_per_contract_mean"]), _f(ps["pnl_at_500"], "%.0f"), _f(ps["pnl_at_50"], "%.0f"), _pct(ps["frac_dates_positive"]),
                     _c(ps["pnl_without_best3_per_contract"]), _pct(ps["frac_in_ramp"]), _pct(ps["ramp_prob_mean"]), ps["n_loo_near_edge"],
                     (" (their P&L %s¢)" % _c(ps["pnl_loo_near_edge"])) if ps["pnl_loo_near_edge"] is not None else ""))
    # signals below threshold, logged anyway
    L.append("### The signal record — %s" % series)
    L.append("Brackets on cleared dates that did not become trades, by reason, with what the gap did against the band alone and against the "
             "band plus friction. Where the legs were not all quoted in the window the friction is the chain-estimated one (protocol amendment 3) "
             "and the bracket is a *signal*, not a trade.\n")
    for snap in bt.SNAPS:
        rows_ok = tradeable_dates(rs, snap)
        bs = [b for r in rows_ok for b in r["brackets"] if b.get("status") == "below_threshold"]
        if bs:
            ex = np.array([b["excess"] for b in bs if b.get("excess") is not None and b["excess"] == b["excess"]])
            g = np.array([b["g"] for b in bs])
            L.append("- %s, legs quoted, below threshold: %d brackets; |gap| > band alone on %s; shortfall to band + friction median %.1f¢ (p90 %.1f¢); gap > 0 on %s."
                     % (snap, len(bs), _pct(np.mean([abs(b["g"]) > b["band90"] for b in bs])), -100 * np.median(ex) if len(ex) else float("nan"),
                        -100 * np.percentile(ex, 10) if len(ex) else float("nan"), _pct(np.mean(g > 0))))
        else:
            L.append("- %s, legs quoted, below threshold: none." % snap)
        un = [dict(b, _date=r["settle_date"]) for r in rows_ok for b in r["brackets"] if b.get("status") == "cme_leg_unquoted"]
        if un:
            est = [b for b in un if b.get("friction_est") is not None]
            wc = [b for b in un if b.get("would_clear_est")]
            fe = np.array([b["friction_est"]["total"] for b in est]) if est else np.array([])
            L.append("- %s, legs not all quoted in the window: %d brackets; |gap| > band alone on %s; estimated friction median %.1f¢ (p10 %.1f¢, p90 %.1f¢); "
                     "**%d would clear band + estimated friction** on %d dates (%s)."
                     % (snap, len(un), _pct(np.mean([abs(b["g"]) > b["band90"] for b in un])), 100 * np.median(fe) if len(fe) else float("nan"),
                        100 * np.percentile(fe, 10) if len(fe) else float("nan"), 100 * np.percentile(fe, 90) if len(fe) else float("nan"),
                        len(wc), len({b.get("_date") for b in wc}), ", ".join(sorted({b.get("_date") or "" for b in wc})) if wc else "—"))
    for snap in bt.SNAPS:
        wc = [dict(b, _date=r["settle_date"]) for r in tradeable_dates(rs, snap) for b in r["brackets"] if b.get("would_clear_est")]
        if not wc:
            continue
        L.append("\nSignals with estimated friction, %s (not trades):\n" % snap)
        L.append("| date | bracket | side | Kalshi exec | Act III | band | gap | est. friction | excess | interior-min | LOO near edge | settled |\n|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|")
        for b in sorted(wc, key=lambda b: (b["_date"], b["lo"])):
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                b["_date"], b["sub_title"], b["side"].replace("_kalshi", " Kalshi"), _f(100 * b["P_exec"], "%.0f¢"), _f(100 * b["pq_mean"], "%.1f¢"),
                _f(100 * b["band90"], "%.1f"), _c(b["g"]), _f(100 * b["friction_est"]["total"], "%.1f"), _f(100 * b["excess_est"], "%.1f"),
                "yes" if b["interior_minimum"] else "", "yes" if b["loo_near_edge"] else "", "yes" if b.get("settled_yes") else "no"))
    L.append("")
    return L


def render(series_list: List[str]) -> str:
    L: List[str] = []
    L.append("# FINDINGS_BACKTEST — extracted densities against Kalshi bracket prices\n")
    L.append("Protocol: `BACKTEST_PROTOCOL.md`, committed %s (`%s`). Extractor frozen at `synth.realchain` arm `%s` (48 knots, Gaussian prior, real intraday "
             "path, 1¢ tick floor). Every number below is computed from `synth/results_backtest/runs_<series>.pkl`; the denominator and bracket logs are the "
             "CSVs next to it. Executable prices only: Kalshi bid/ask closes of the stored 1-minute candle at the snapshot minute, CME TBBO last quotes in the window.\n"
             % (_git(["log", "-1", "--format=%cI", "--", "BACKTEST_PROTOCOL.md"]), _git(["log", "-1", "--format=%h", "--", "BACKTEST_PROTOCOL.md"]), bt.ARM))
    L.append("**VERDICT_PLACEHOLDER**\n")
    rs = load(series_list[0])
    V = verdict(rs)
    L.append("## 0. The bar, mechanically (protocol §2, %s, lead snapshot %s)\n" % (series_list[0], bt.LEAD_SNAP))
    L.append("| condition | holds | detail |\n|---|---|---|")
    L.append("| B1 structure exists | **%s** | %s |" % ("yes" if V["B1"] else "no", V["B1_reason"]))
    d2 = V["B2_detail"]
    L.append("| B2 tradeable edge | **%s** | filtered brackets from %d dates in %d months; sign agreement with B1's direction (%s): %s |"
             % ("yes" if V["B2"] else "no", d2["n_dates"], d2["n_months"], d2["direction"] or "none", _pct(d2["sign_agreement"])))
    d3 = V["B3_detail"]
    L.append("| B3 survives friction at size | **%s** | %s trades; P&L %s¢ per contract summed; dates positive %s; without best three %s¢ |"
             % ("yes" if V["B3"] else "no", d3["n"], _c(d3["pnl_total_per_contract"]), _pct(d3["frac_dates_positive"]), _c(d3["pnl_without_best3_per_contract"])))
    L.append("| **mechanical verdict** | **%s** | EDGE needs all three; STRUCTURE needs B1; otherwise NULL |\n" % V["verdict"])
    L.append("## 1. KXWTIW — the study\n")
    L.extend(render_series(rs, series_list[0], True))
    A = artifact_checks(rs)
    L.append("## 2. Artifact checks (protocol §7)\n")
    L.append("- **Residual forward error.** Median |E[F] − F₀| at %s: %s¢; correlation of the per-date mean gap with it: %s." % (
        bt.LEAD_SNAP, _f(A.get("forward_error_cents_median_abs"), "%.1f"), _f(A.get("corr_gap_vs_forward_error"))))
    if "pairs" in A:
        L.append("- **Asynchronicity / snapshot dependence.** %d brackets quoted at both snapshots: gap sign agrees on %s, correlation %s. Path sources by snapshot: %s."
                 % (A["pairs"], _pct(A["sign_agreement_snapshots"]), _f(A.get("corr_snapshots")), json.dumps({k: {kk: int(vv) for kk, vv in v.items()} for k, v in A["path_sources"].items()})))
    cd = A.get("chain_digital")
    if cd:
        L.append("- **Extractor-independence.** The chain's own outer-condor digital (mid, four legs, parity-converted) against Act III on %d brackets: mean |chain − Act III| %.1f¢; "
                 "Kalshi − chain digital %+.1f¢ vs Kalshi − Act III %+.1f¢; the two disagreements have the same sign on %s of brackets." % (
                     cd["n"], cd["mean_abs_chain_minus_pq_cents"], cd["mean_kalshi_minus_chain_cents"], cd["mean_kalshi_minus_pq_cents"], _pct(cd["frac_same_sign"])))
    L.append("- **One-snapshot systematic error.** Stage 18 by snapshot is in §1's pooled table; B1 requires both snapshots to agree.\n")
    for s in series_list[1:]:
        rs2 = load(s)
        if not rs2:
            continue
        L.append("## 3. %s — the secondary arm (own denominator, never pooled into the bar)\n" % s)
        V2 = verdict(rs2)
        L.append("Mechanical reading on the same conditions, for the record only: B1 %s, B2 %s, B3 %s → %s. %s\n" % (
            "yes" if V2["B1"] else "no", "yes" if V2["B2"] else "no", "yes" if V2["B3"] else "no", V2["verdict"], V2["B1_reason"]))
        L.extend(render_series(rs2, s, False))
    L.append("## 4. Plots\n")
    for s in series_list:
        if (PLOTS / ("gap_by_moneyness_%s.png" % s)).exists():
            L.append("![gap](synth/plots_backtest/gap_by_moneyness_%s.png)\n![tail gap by date](synth/plots_backtest/tail_gap_by_date_%s.png)\n" % (s, s))
    L.append("## 5. Reading\n")
    L.append("READING_PLACEHOLDER\n")
    L.append("## 6. Parameters and assumptions in force\n")
    L.append("`KALSHI_FEE_COEF=%.2f` (taker, maker 0), `CME_FEE_PER_LEG=$%.2f`, `CME_EXIT_FRACTION=%.1f`, `SPREAD_WIDTH=$%.2f`, size %d Kalshi contracts per standard-CL structure "
             "(%d on Micro, not available on weekly dates), Kalshi bar staleness ≤ %.0f min, executable price in [%.0f¢, %.0f¢], band ≤ %.0f¢, trough dip %.0f%%, LOO proximity $%.2f. "
             "The fee figures are assumptions to verify against the live schedules; the filter's friction uses measured half-spreads per trade.\n" % (
                 bt.KALSHI_FEE_COEF, bt.CME_FEE_PER_LEG, bt.CME_EXIT_FRACTION, bt.SPREAD_WIDTH, bt.SIZE_APPLICABLE, bt.SIZE_DEPTH_CLEARED, bt.KALSHI_STALE_MAX_MIN,
                 100 * bt.PRICE_MIN, 100 * bt.PRICE_MAX, 100 * bt.BAND_MAX, 100 * bt.TROUGH_DIP, bt.LOO_NEAR_EDGE))
    return "\n".join(L)


def main(argv: Optional[List[str]] = None) -> int:
    series = [s for s in ("KXWTIW", "KXWTI") if bt.runs_path(s).exists()]
    if not series:
        print("no runs on disk")
        return 1
    for s in series:
        plots(load(s), s)
    text = render(series)
    out = ROOT / "FINDINGS_BACKTEST.md"
    tmp = out.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(out)
    V = verdict(load(series[0]))
    with open(bt.RESULTS / "verdict.json", "w") as fh:
        json.dump(V, fh, indent=1, default=str)
    print("wrote", out, "mechanical verdict:", V["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
