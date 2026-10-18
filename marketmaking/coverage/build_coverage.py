"""Build the Kalshi ladder COVERAGE MAP: which numeric ladders nobody is paid to quote.

Question
--------
Kalshi subsidises liquidity through two channels:

  1. the Liquidity Provider Program (LPP) -- named professional firms with a
     designated-market-maker obligation on a named set of series. Scraped to a
     dated snapshot by marketmaking/lpp/build_snapshot.py.
  2. the retail Liquidity Incentive Program (LIP) -- per-market cash rewards
     any account can earn by quoting inside a target. Snapshotted by
     marketmaking/coverage/fetch_lip.py from the keyless public endpoint.

A series with neither is a series where we would not be quoting head-to-head
against someone whose economics are better than ours by construction. This
script ranks every numeric ladder series by how much *tight-spread* volume sits
in the uncovered set.

Inputs (all committed / staged under marketmaking/data/_import and
marketmaking/lpp; nothing is fetched from the network by this script)
---------------------------------------------------------------------
  waves_data_discovery_events.parquet   801,032 events. is_ladder := n_numeric >= 3.
  waves_data_discovery_markets.parquet  5,232,426 markets, POINT-IN-TIME at
                                        2026-10-05T22:0x CDT. `volume` is
                                        lifetime-per-market; yes_bid/yes_ask is
                                        ONE observation. Every spread number
                                        derived from it is labelled "snapshot".
  ladder_results_summary.parquet        2,194 ladder events, 129 series, with
                                        MEASURED minute-grid spread history.
                                        Used only to validate the snapshot proxy.
  lpp/lpp_<date>.json                   dated LPP snapshot.
  coverage/lip_<date>.json              dated retail-LIP snapshot.

Definitions that matter
-----------------------
quoted (snapshot)   a market with status == "active" at the snapshot whose
                    yes_bid > 0 and yes_ask < 100. The parquet encodes "no bid"
                    as 0 and "no ask" as 100, so both-sided means both strict.
snap_spread         yes_ask - yes_bid, in cents, on quoted markets only.
volume_365d         sum of lifetime per-market volume over the series' ladder
                    markets that either were still active at the snapshot or
                    closed within 365 days before it. Excludes long-dead
                    listings whose lifetime volume is an archaeological print.
tight_share_2c      share of quoted active markets with snap_spread <= 2.0c.
TIGHT-SPREAD VOLUME volume_365d * tight_share_2c.
                    Rationale: raw volume ranks series we could never quote
                    competitively (a 20c-wide book trading size is not
                    accessible to a maker who has to be inside); tight share
                    alone ranks dead series with one lucky tight print. The
                    product estimates the portion of recent traded volume that
                    occurs in a regime where a <=2c two-sided market exists --
                    i.e. the volume actually reachable by a maker who must quote
                    at or inside 2c. It is an ESTIMATE: the share is one
                    observation and the volume is a 365d total, so the two
                    factors are not measured over the same window. The
                    validation section quantifies how wrong the share factor is.

Coverage rule (the expensive-error rule)
----------------------------------------
Eight LPP rows name no tickers at all ("Hourly Weather", "Crypto 15min
markets", ...). A series that plausibly matches one of those descriptions is
tagged coverage_status="unknown", NEVER "uncovered". Mislabelling a covered
series as uncovered puts us head-to-head with a designated provider while
believing the series is empty, which is the costly direction. Each heuristic is
named in the `unknown_reason` column so the reader can audit it.

Outputs (written next to this file)
-----------------------------------
  coverage.csv              one row per ladder series
  validation_spread.csv     per-series snapshot-vs-measured comparison
  coverage_meta.json        reconciliation counts, snapshot ids, run digest

Determinism: no network, no clock-dependent branching except `generated_at`
(excluded from the digest). Re-running reproduces coverage.csv byte-for-byte.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
MM = HERE.parent
IMP = MM / "data" / "_import"

EVENTS = IMP / "waves_data_discovery_events.parquet"
MARKETS = IMP / "waves_data_discovery_markets.parquet"
MEASURED = IMP / "ladder_results_summary.parquet"

TIGHT_C = 2.0          # the headline tightness threshold
RECENT_DAYS = 365
MIN_QUOTED_FOR_SHARE = 5   # below this the snapshot share is reported but flagged

# The ladder/ module's own census calls a bracket "tight" at spread <= 10c
# (ladder/census.py SPREAD_CAP = 10.0). The validation section compares like
# with like at that threshold, not at our 2c headline.
LADDER_MODULE_SPREAD_CAP = 10.0


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------
def latest(pattern: str, where: pathlib.Path) -> pathlib.Path:
    hits = sorted(where.glob(pattern))
    if not hits:
        raise SystemExit("no file matching %s in %s" % (pattern, where))
    return hits[-1]


def load_lpp(path: pathlib.Path) -> dict:
    d = json.loads(path.read_text())
    return {
        "path": path.name,
        "date": d["snapshot_date"],
        "providers": d["provider_count_by_ticker"],
        "groups": d["groups_by_ticker"],
        "prose_rows": [r["group"] for r in d["prose_rows"]],
        "n_rows": d["n_rows"],
    }


def load_lip(path: pathlib.Path) -> dict:
    d = json.loads(path.read_text())
    # Per-period reward pool: for each distinct market the largest period_reward
    # any of its programs offers, summed. Markets carry several programs with
    # non-overlapping (sometimes future-dated) windows, so summing raw programs
    # would double count calendar periods. period_reward is centi-cents.
    best: dict[str, dict] = {}
    for p in d["programs"]:
        mt = p.get("market_ticker") or ""
        if not mt:
            continue
        usd = (p.get("period_reward") or 0) / 10000.0
        cur = best.get(mt)
        if cur is None or usd > cur["usd"]:
            best[mt] = {"usd": usd, "series": p["series"]}
    agg: dict[str, dict] = {}
    for mt, v in best.items():
        e = agg.setdefault(v["series"], {"markets": 0, "pool_usd": 0.0, "per_market": []})
        e["markets"] += 1
        e["pool_usd"] += v["usd"]
        e["per_market"].append(v["usd"])
    nprog: dict[str, int] = {}
    for p in d["programs"]:
        nprog[p["series"]] = nprog.get(p["series"], 0) + 1
    for s, e in agg.items():
        e["n_programs"] = nprog.get(s, 0)
        e["median_usd"] = float(np.median(e.pop("per_market")))
        e["pool_usd"] = round(e["pool_usd"], 2)
    return {
        "path": path.name,
        "date": d["snapshot_date"],
        "by_series": agg,
        "n_programs": d["n_programs"],
        "n_series": d["n_series"],
        "pagination": d["pagination"],
        "exhaustive": d.get("exhaustive", False),
    }


# --------------------------------------------------------------------------
# cadence
# --------------------------------------------------------------------------
CADENCE_BINS = [
    (20 * 60, "15min"),
    (2 * 3600, "hourly"),
    (8 * 3600, "intraday"),
    (36 * 3600, "daily"),
    (10 * 86400, "weekly"),
    (45 * 86400, "monthly"),
    (200 * 86400, "quarterly"),
]


def cadence_label(sec: float) -> str:
    if not np.isfinite(sec):
        return "single"
    for lim, name in CADENCE_BINS:
        if sec <= lim:
            return name
    return "annual_or_longer"


def derive_cadence(ev_close: pd.DataFrame) -> pd.DataFrame:
    """Median gap between consecutive event close times inside a series."""
    out = []
    for s, g in ev_close.groupby("series", sort=True):
        t = np.sort(g["close_epoch"].values)
        gap = np.median(np.diff(t)) if len(t) > 1 else np.nan
        out.append((s, float(gap) if np.isfinite(gap) else np.nan, cadence_label(gap)))
    return pd.DataFrame(out, columns=["series", "event_gap_sec_median", "cadence"])


# --------------------------------------------------------------------------
# prose-row heuristics -> coverage_status "unknown"
# --------------------------------------------------------------------------
FX_RE = re.compile(r"(EURUSD|GBPUSD|USDJPY|USDCAD|AUDUSD|USDCHF|NZDUSD|USDMXN|USDCNH|DXY|FX)")
PRIMARY_COMMOD_RE = re.compile(r"(BRENT|CORN|GOLD|SILVER|COPPER)")
RT_RE = re.compile(r"(ROTTEN|TOMATO)")
INTRADAY = {"15min", "hourly", "intraday"}


def unknown_reason(series: str, category: str, cadence: str, title: str) -> str:
    """Return the prose LPP row this series plausibly falls under, else ""."""
    s, t = series.upper(), (title or "").upper()
    if RT_RE.search(s) or RT_RE.search(t) or s == "KXRT":
        return "prose:Rotten Tomatoes"
    if category == "Crypto":
        if cadence == "15min" or s.endswith("15M"):
            return "prose:Crypto 15min markets"
        if cadence in ("hourly", "intraday", "daily"):
            return "prose:Crypto Hourly & Daily"
    if category == "Climate and Weather" and cadence in ("15min", "hourly", "intraday"):
        return "prose:Hourly Weather"
    if category in ("Commodities", "Economics"):
        if cadence in ("15min",):
            return "prose:Commodities 15min markets"
        if cadence in ("hourly", "intraday"):
            return "prose:Hourly Commodities"
        if PRIMARY_COMMOD_RE.search(s) and cadence in ("daily", "weekly"):
            return "prose:Primary Daily & Weekly Commodities"
    if cadence == "15min" and FX_RE.search(s):
        return "prose:FX 15min markets"
    return ""


# --------------------------------------------------------------------------
# main build
# --------------------------------------------------------------------------
def build(lpp_path: pathlib.Path, lip_path: pathlib.Path) -> dict:
    lpp = load_lpp(lpp_path)
    lip = load_lip(lip_path)

    ev = pd.read_parquet(EVENTS)
    lad = ev[ev.is_ladder].copy()
    ladder_series = sorted(lad.series.unique())

    mk = pd.read_parquet(MARKETS, columns=[
        "ticker", "event_ticker", "series", "category", "status",
        "open_epoch", "close_epoch", "volume", "open_interest", "yes_bid", "yes_ask"])
    lm = mk[mk.event_ticker.isin(set(lad.event_ticker))].copy()

    snapshot_epoch = int(lm.loc[lm.status == "active", "close_epoch"].min())
    # the newest finalized close is the true "as of"; active closes start just after
    as_of = int(mk.loc[mk.status == "finalized", "close_epoch"].max())
    recent_cut = as_of - RECENT_DAYS * 86400

    # ---- event-level close times for cadence
    ev_close = (lm.groupby(["series", "event_ticker"], sort=False)["close_epoch"]
                  .max().reset_index())
    cad = derive_cadence(ev_close[["series", "close_epoch"]])

    # ---- volume aggregates
    lm["recent"] = (lm.close_epoch >= recent_cut) | (lm.status == "active")
    g = lm.groupby("series", sort=True)
    base = pd.DataFrame({
        "n_markets": g.size(),
        "volume_lifetime": g.volume.sum(),
        "open_interest": g.open_interest.sum(),
    })
    rec = lm[lm.recent]
    base["volume_365d"] = rec.groupby("series").volume.sum()
    base["n_markets_365d"] = rec.groupby("series").size()
    base["n_markets_365d_traded"] = rec[rec.volume > 0].groupby("series").size()
    # concentration: share of 365d volume in the single largest market
    top1 = rec.groupby("series").volume.max()
    base["vol365_top1_share"] = (top1 / base["volume_365d"]).where(base["volume_365d"] > 0)
    base = base.fillna({"volume_365d": 0.0, "n_markets_365d": 0, "n_markets_365d_traded": 0})

    # ---- snapshot spread stats on quoted active markets
    act = lm[lm.status == "active"].copy()
    act["quoted"] = (act.yes_bid > 0) & (act.yes_ask < 100)
    q = act[act.quoted].copy()
    q["spread"] = q.yes_ask - q.yes_bid
    qg = q.groupby("series", sort=True)
    snap = pd.DataFrame({
        "n_active": act.groupby("series").size(),
        "n_quoted_active": qg.size(),
        "snap_spread_median_c": qg.spread.median(),
        "snap_spread_mean_c": qg.spread.mean(),
        "tight_share_1c": qg.spread.apply(lambda x: float((x <= 1.0).mean())),
        "tight_share_2c": qg.spread.apply(lambda x: float((x <= 2.0).mean())),
        "tight_share_3c": qg.spread.apply(lambda x: float((x <= 3.0).mean())),
        "tight_share_10c": qg.spread.apply(lambda x: float((x <= LADDER_MODULE_SPREAD_CAP).mean())),
    })

    cat = (lad.groupby("series").category
              .agg(lambda s: s.mode().iat[0] if len(s.mode()) else ""))
    title = lad.sort_values("event_ticker").groupby("series").title.last()
    nev = lad.groupby("series").size().rename("n_events")
    strike_period = (lad.groupby("series").strike_period
                        .agg(lambda s: s.mode().iat[0] if len(s.mode()) else ""))

    df = pd.DataFrame(index=pd.Index(ladder_series, name="series"))
    df = (df.join(cat.rename("category")).join(nev).join(strike_period.rename("strike_period"))
            .join(base).join(snap).join(cad.set_index("series")).join(title.rename("example_title")))
    df["n_active"] = df["n_active"].fillna(0).astype(int)
    df["n_quoted_active"] = df["n_quoted_active"].fillna(0).astype(int)
    df["n_markets_365d_traded"] = df["n_markets_365d_traded"].fillna(0).astype(int)

    # ---- the headline metric
    df["tight_spread_volume"] = df["volume_365d"] * df["tight_share_2c"]
    df["tight_spread_volume"] = df["tight_spread_volume"].fillna(0.0)
    df["thin_snapshot"] = df["n_quoted_active"] < MIN_QUOTED_FOR_SHARE
    df["likely_artifact"] = (
        ((df["n_markets_365d_traded"] <= 2) & (df["volume_365d"] > 0))
        | (df["vol365_top1_share"] > 0.95)
        | (df["n_active"] == 0)
    )

    # ---- LPP join (explicit tickers only; prose handled separately)
    df["lpp_covered"] = df.index.map(lambda s: s in lpp["providers"])
    df["lpp_provider_count"] = df.index.map(lambda s: lpp["providers"].get(s, 0)).astype(int)
    df["lpp_group"] = df.index.map(lambda s: "; ".join(lpp["groups"].get(s, [])))

    # ---- LIP join
    lipb = lip["by_series"]
    df["lip_active"] = df.index.map(lambda s: s in lipb)
    df["lip_n_programs"] = df.index.map(lambda s: lipb.get(s, {}).get("n_programs", 0)).astype(int)
    df["lip_n_markets"] = df.index.map(lambda s: lipb.get(s, {}).get("markets", 0)).astype(int)
    df["lip_reward_per_period_usd"] = df.index.map(
        lambda s: lipb.get(s, {}).get("pool_usd", 0.0)).astype(float)
    df["lip_reward_per_market_usd"] = df.index.map(
        lambda s: lipb.get(s, {}).get("median_usd", 0.0)).astype(float)

    # ---- coverage status
    df = df.reset_index()
    df["unknown_reason"] = [
        unknown_reason(s, c, cd, t)
        for s, c, cd, t in zip(df.series, df.category, df.cadence, df.example_title)]
    status = []
    for covered, unk in zip(df.lpp_covered | df.lip_active, df.unknown_reason):
        if covered:
            status.append("covered")
        elif unk:
            status.append("unknown")
        else:
            status.append("uncovered")
    df["coverage_status"] = status
    df["coverage_source"] = np.where(
        df.lpp_covered & df.lip_active, "lpp+lip",
        np.where(df.lpp_covered, "lpp", np.where(df.lip_active, "lip", "")))
    df["lpp_snapshot"] = lpp["path"]
    df["lip_snapshot"] = lip["path"]

    cols = ["series", "category", "cadence", "event_gap_sec_median", "strike_period",
            "n_events", "n_markets", "n_active", "n_quoted_active",
            "volume_lifetime", "volume_365d", "n_markets_365d", "n_markets_365d_traded",
            "vol365_top1_share", "open_interest",
            "snap_spread_median_c", "snap_spread_mean_c",
            "tight_share_1c", "tight_share_2c", "tight_share_3c", "tight_share_10c",
            "tight_spread_volume", "thin_snapshot", "likely_artifact",
            "lpp_covered", "lpp_provider_count", "lpp_group",
            "lip_active", "lip_n_programs", "lip_n_markets",
            "lip_reward_per_period_usd", "lip_reward_per_market_usd",
            "coverage_status", "coverage_source", "unknown_reason",
            "lpp_snapshot", "lip_snapshot", "example_title"]
    df = df[cols].sort_values(["tight_spread_volume", "series"], ascending=[False, True])

    # ---- validation of the snapshot proxy against measured minute-grid stats
    val = validate(df, lpp, lip)

    meta = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "snapshot_as_of_epoch": as_of,
        "snapshot_as_of_utc": dt.datetime.fromtimestamp(as_of, dt.timezone.utc).isoformat(),
        "first_active_close_epoch": snapshot_epoch,
        "recent_window_days": RECENT_DAYS,
        "tight_threshold_c": TIGHT_C,
        "lpp_snapshot": lpp["path"], "lpp_snapshot_date": lpp["date"],
        "lpp_rows": lpp["n_rows"], "lpp_prose_rows": lpp["prose_rows"],
        "lip_snapshot": lip["path"], "lip_snapshot_date": lip["date"],
        "lip_n_programs": lip["n_programs"], "lip_n_series": lip["n_series"],
        "lip_pagination": lip["pagination"], "lip_exhaustive": lip["exhaustive"],
        "reconciliation": {
            "events_total": int(len(ev)),
            "ladder_events": int(len(lad)),
            "ladder_series_from_events": int(lad.series.nunique()),
            "ladder_series_in_output": int(len(df)),
            "ladder_markets": int(len(lm)),
            "markets_total": int(len(mk)),
            "active_ladder_markets": int(len(act)),
            "quoted_active_ladder_markets": int(act.quoted.sum()),
        },
        "status_counts": df.coverage_status.value_counts().to_dict(),
        "tight_spread_volume_by_status": df.groupby("coverage_status")
                                           .tight_spread_volume.sum().round(1).to_dict(),
        "validation": val["summary"],
    }

    (HERE / "coverage.csv").write_text(df.to_csv(index=False, float_format="%.6g"))
    val["table"].to_csv(HERE / "validation_spread.csv", index=False, float_format="%.6g")
    digest = hashlib.sha256((HERE / "coverage.csv").read_bytes()).hexdigest()
    meta["coverage_csv_sha256"] = digest
    (HERE / "coverage_meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    return {"df": df, "meta": meta, "validation": val}


def validate(df: pd.DataFrame, lpp: dict, lip: dict) -> dict:
    """Compare the snapshot spread proxy with the measured minute-grid stats.

    ladder_results_summary.parquet carries, per ladder event, the number of
    bracket-minutes that were two-sided (quoted_bracket_minutes) and the subset
    of those whose spread was <= 10c (tight_bracket_minutes, ladder/census.py
    SPREAD_CAP), plus the median spread over the event. Aggregating to series
    gives a measured tight-share and a minutes-weighted median spread to put
    against the one-observation snapshot.
    """
    me = pd.read_parquet(MEASURED, columns=[
        "series", "event", "quoted_bracket_minutes", "tight_bracket_minutes",
        "spread_median", "minutes", "brackets"])
    g = me.groupby("series")
    meas = pd.DataFrame({
        "meas_events": g.size(),
        "meas_quoted_minutes": g.quoted_bracket_minutes.sum(),
        "meas_tight_minutes": g.tight_bracket_minutes.sum(),
    })
    meas["meas_tight_share_10c"] = meas.meas_tight_minutes / meas.meas_quoted_minutes
    # minutes-weighted mean of the per-event median spread
    w = me.dropna(subset=["spread_median"])
    meas["meas_spread_median_c"] = (
        w.assign(x=w.spread_median * w.quoted_bracket_minutes)
         .groupby("series").x.sum() / w.groupby("series").quoted_bracket_minutes.sum())

    snap = df.set_index("series")[[
        "snap_spread_median_c", "tight_share_10c", "tight_share_2c",
        "n_quoted_active", "volume_365d", "coverage_status", "category", "cadence"]]
    j = meas.join(snap, how="left")
    j["in_ladder_census"] = j.snap_spread_median_c.notna() | j.n_quoted_active.notna()
    tab = j.reset_index()

    ok = j.dropna(subset=["snap_spread_median_c", "meas_spread_median_c"])
    ok = ok[ok.n_quoted_active >= MIN_QUOTED_FOR_SHARE]
    okt = j.dropna(subset=["tight_share_10c", "meas_tight_share_10c"])
    okt = okt[okt.n_quoted_active >= MIN_QUOTED_FOR_SHARE]

    def _corr(a, b, method):
        if len(a) < 3:
            return float("nan")
        return float(pd.Series(a.values).corr(pd.Series(b.values), method=method))

    summary = {
        "measured_series": int(len(meas)),
        "measured_series_in_ladder_census": int(j.n_quoted_active.notna().sum()),
        "comparable_series_spread": int(len(ok)),
        "comparable_series_tight": int(len(okt)),
        "spread_spearman": _corr(ok.snap_spread_median_c, ok.meas_spread_median_c, "spearman"),
        "spread_pearson": _corr(ok.snap_spread_median_c, ok.meas_spread_median_c, "pearson"),
        "spread_median_bias_c": float((ok.snap_spread_median_c - ok.meas_spread_median_c).median())
        if len(ok) else float("nan"),
        "spread_median_abs_err_c": float((ok.snap_spread_median_c - ok.meas_spread_median_c).abs().median())
        if len(ok) else float("nan"),
        "tight10_spearman": _corr(okt.tight_share_10c, okt.meas_tight_share_10c, "spearman"),
        "tight10_pearson": _corr(okt.tight_share_10c, okt.meas_tight_share_10c, "pearson"),
        "tight10_median_bias": float((okt.tight_share_10c - okt.meas_tight_share_10c).median())
        if len(okt) else float("nan"),
        "tight10_median_abs_err": float((okt.tight_share_10c - okt.meas_tight_share_10c).abs().median())
        if len(okt) else float("nan"),
    }
    return {"table": tab, "summary": summary, "ok_spread": ok, "ok_tight": okt}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lpp", default=None, help="path to an lpp_*.json snapshot")
    ap.add_argument("--lip", default=None, help="path to a lip_*.json snapshot")
    a = ap.parse_args()
    lpp_path = pathlib.Path(a.lpp) if a.lpp else latest("lpp_*.json", MM / "lpp")
    lip_path = pathlib.Path(a.lip) if a.lip else latest("lip_*.json", HERE)
    res = build(lpp_path, lip_path)
    m = res["meta"]
    print("ladder series: %d  (events say %d)"
          % (m["reconciliation"]["ladder_series_in_output"],
             m["reconciliation"]["ladder_series_from_events"]))
    print("status:", m["status_counts"])
    print("tight-spread volume by status:", m["tight_spread_volume_by_status"])
    print("validation:", json.dumps(m["validation"], indent=2))
    print("coverage.csv sha256:", m["coverage_csv_sha256"])


if __name__ == "__main__":
    main()
