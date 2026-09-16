#!/usr/bin/env python3
"""Tests for the V2 real-chain changes (synth/sync.py, synth/detector.py, black76 with
per-quote F and T). Fast: Laplace sampler, no data_cme/ needed.

    python3 -m unittest test_realchain_v2 -v        (~20 s)
"""

import os
import sys
import unittest

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from synth import black76, densities, detector, geometry, noise, sync  # noqa: E402

F_REF, SIGMA, T_REF = 90.0, 1.2, 1.0 / 365.0
D = 1.0
YEAR_SEC = 365.0 * 86400.0


def _smile(k):
    return SIGMA + 0.8 * k + 2.0 * k * k   # a skewed, curved sticky-moneyness smile


def _chain():
    K = np.arange(80.0, 100.01, 0.5)
    R = np.where(K < F_REF, "P", "C")
    return K, R


class TestBlack76Arrays(unittest.TestCase):
    def test_implied_vol_accepts_per_quote_F_and_T(self):
        K = np.array([85.0, 90.0, 95.0, 88.0])
        F = np.array([89.5, 90.0, 90.7, 90.2])
        T = np.array([1.0, 1.1, 0.9, 1.05]) / 365.0
        R = np.array(["P", "C", "C", "P"])
        sig = np.array([1.1, 1.2, 1.3, 1.15])
        price = black76.price(F, K, T, sig, D, R)
        got = black76.implied_vol(price, F, K, T, D, R)
        np.testing.assert_allclose(got, sig, atol=1e-6)


class TestAdjust(unittest.TestCase):
    def test_sticky_strike_reprice_is_exact_when_vols_are_sticky(self):
        # quotes taken at different underlying levels and times; each strike's vol unchanged
        K, R = _chain()
        rng = np.random.default_rng(0)
        t_min = rng.uniform(0, 60, K.size)
        F_t = F_REF - 0.02 * t_min + 0.3 * np.sin(t_min / 7.0)   # a $1.2 drift plus wiggles
        T_t = T_REF + t_min * 60.0 / YEAR_SEC
        sig_K = _smile(np.log(K / F_REF))
        p_t = black76.price(F_t, K, T_t, sig_K, D, R)
        p_ref = black76.price(F_REF, K, T_REF, sig_K, D, R)
        hs = 0.01
        path = {"knots_min": np.linspace(0, 60, 61), "values": np.interp(np.linspace(0, 60, 61), np.sort(t_min), F_t[np.argsort(t_min)]),
                "smile": sync.Smile(np.array([2.0, 0.8, SIGMA]), -0.2, 0.2, SIGMA)}
        # use the exact path at the quote times so the test isolates the reprice
        path["values"] = np.interp(np.linspace(0, 60, 61), np.sort(t_min), F_t[np.argsort(t_min)])
        F_exact = np.interp(t_min, path["knots_min"], path["values"])
        p_t_on_path = black76.price(F_exact, K, T_t, sig_K, D, R)
        a = sync.adjust(K, R, p_t_on_path - hs, p_t_on_path + hs, t_min, path, F_REF, T_REF, D, mode="strike")
        big = p_ref > 0.03  # quotes at the floor are not moved by design
        np.testing.assert_allclose(a["mid"][big], p_ref[big], atol=2e-4)
        self.assertTrue(np.all(a["hs"][big] - hs < 1e-9))
        # the shift is dominated by delta on a $1 move, but theta is present too
        self.assertGreater(np.abs(a["adj_delta"]).max(), 0.05)
        self.assertGreater(np.abs(a["adj_theta"]).max(), 0.005)

    def test_floor_quotes_are_left_alone_and_bid_stays_positive(self):
        K = np.array([60.0, 120.0])
        R = np.array(["P", "C"])
        path = {"knots_min": np.array([0.0, 60.0]), "values": np.array([F_REF, F_REF - 2.0]), "smile": sync.Smile(np.array([SIGMA]), -1, 1, SIGMA)}
        a = sync.adjust(K, R, np.array([0.01, 0.01]), np.array([0.02, 0.02]), np.array([30.0, 30.0]), path, F_REF, T_REF, D)
        np.testing.assert_allclose(a["adj"], 0.0)
        self.assertTrue(np.all(a["bid"] > 0))
        self.assertEqual(list(a["how"]), ["floor", "floor"])


class TestPath(unittest.TestCase):
    def _events(self, rng, path_fn, n=400, noise_c=0.01):
        K, R = _chain()
        rows = []
        t_ref = pd.Timestamp("2026-03-12 19:30:00", tz="UTC")
        for _ in range(n):
            t = float(rng.uniform(0, 60))
            i = int(rng.integers(K.size))
            F_t = path_fn(t)
            T_t = T_REF + t * 60.0 / YEAR_SEC
            sig = _smile(np.log(K[i] / F_t))
            p = float(black76.price(F_t, K[i], T_t, sig, D, R[i]))
            hs = max(0.005, 0.01 + 0.02 * p)
            mid = p + rng.normal(0, noise_c)
            rows.append({"ts_event": t_ref - pd.Timedelta(minutes=t), "strike": K[i], "right": R[i],
                         "bid_px_00": max(round(mid - hs, 2), 0.01), "ask_px_00": max(round(mid + hs, 2), 0.02)})
        return pd.DataFrame(rows), t_ref

    def test_recovers_the_shape_of_a_planted_path(self):
        rng = np.random.default_rng(1)
        drift = lambda t: F_REF + 0.02 * t - 1.0 * (t < 20)   # $1 step 20 minutes before the reference, plus a trend
        ev, t_ref = self._events(rng, drift)
        path = sync.estimate_path(ev, t_ref, T_REF, drift(0.0), D, SIGMA, 60.0, anchor_min=0.0)
        self.assertTrue(path["ok"], path.get("reason"))
        self.assertGreater(path["n_informative"], 50)
        truth = np.array([drift(t) for t in path["knots_min"]])
        err = path["values"] - truth
        away = np.abs(path["knots_min"] - 20.0) > 1.5   # a step exactly at a knot is not representable by a 1-minute piecewise-linear path
        self.assertLess(np.sqrt(np.mean(err[away] ** 2)), 0.08, "path rms error $%.3f" % np.sqrt(np.mean(err[away] ** 2)))
        self.assertLess(np.sqrt(np.mean(err ** 2)), 0.15)
        self.assertLess(abs(path["anchor_drift_cents"]), 1e-9)   # anchored at the reference instant
        self.assertLess(abs(path["level_offset_cents"]), 5.0)      # options-implied level agrees with the true one

    def test_anchor_at_an_earlier_minute_carries_the_last_move(self):
        rng = np.random.default_rng(2)
        drift = lambda t: F_REF - 0.5 * max(1.0 - t, 0.0)   # 50c slide over the last minute
        ev, t_ref = self._events(rng, drift, n=800)
        settle = F_REF   # the level at 1 minute before the reference
        path = sync.estimate_path(ev, t_ref, T_REF, settle, D, SIGMA, 60.0, anchor_min=1.0)
        self.assertTrue(path["ok"])
        # the last minute holds ~13 events and the random-walk prior shrinks a 50c one-minute move: expect most of it, not all
        self.assertLess(abs(path["F_at_ref"] - (F_REF - 0.5)), 0.20, "F_at_ref %.3f" % path["F_at_ref"])
        self.assertLess(abs(path["anchor_drift_cents"] + 50.0), 20.0)
        self.assertLess(path["anchor_drift_cents"], -30.0)

    def test_too_few_events_falls_back_to_flat(self):
        rng = np.random.default_rng(3)
        ev, t_ref = self._events(rng, lambda t: F_REF, n=3)
        path = sync.estimate_path(ev, t_ref, T_REF, F_REF, D, SIGMA, 60.0)
        self.assertFalse(path["ok"])
        np.testing.assert_allclose(path["values"], F_REF)
        self.assertEqual(path["F_at_ref"], F_REF)


class TestDetector(unittest.TestCase):
    def setUp(self):
        geo = geometry.load()
        snap = geometry.snapshots(geo)[2]
        self.F0, self.T = float(snap["forward"]), float(snap["T_years"])
        self.sigma = float(np.clip(snap["atm_iv"] or 0.6, 0.2, 2.0))
        self.K = np.array(snap["strikes"], float)
        self.R = np.array(snap["rights"])
        self.pl = densities.Planted("crude_skew", self.F0, self.sigma, self.T)
        self.edges = densities.kalshi_edges(self.F0)
        rng = np.random.default_rng(0)
        C = self.pl.price(self.K, self.R)
        hs = noise.half_spreads(rng, C, geo["half_spread_model"], 1.0, observed=np.array(snap["half_spreads"]))
        _, _, self.mid, self.hs = noise.quotes(rng, C, hs, "gaussian")
        self.nuts = {"n_chains": 4, "n_warmup": 50, "n_samples": 200}

    def test_consistent_chain_passes_split_half_and_loo(self):
        sh = detector.split_half(self.K, self.R, self.mid, self.hs, self.F0, self.pl.D, self.T, self.sigma, 0.02, self.edges, self.nuts, sampler="laplace", cutoff=3.0)
        self.assertLess(sh["max_abs_z"], 3.0, sh["max_abs_z"])
        self.assertFalse(sh["fired"])
        self.assertEqual(sum(sh["n_per_half"]), len(self.K))
        lo = detector.loo(self.K, self.R, self.mid, self.hs, self.F0, self.pl.D, self.T, self.sigma, 0.02)
        self.assertEqual(lo["n_flagged"], 0, lo["z"])
        self.assertLess(lo["rms_z"], 1.5)
        g = detector.gate(sh, lo, detector.act2_signal(None, sh["halves"][0]["mean"], len(self.K)))
        self.assertFalse(g["fired"])

    def test_loo_localises_a_stale_quote(self):
        mid = self.mid.copy()
        calls = np.where(self.R == "C")[0]
        i = int(calls[2])
        mid[i] = max(mid[i] - 0.15, 0.005)
        lo = detector.loo(self.K, self.R, mid, self.hs, self.F0, self.pl.D, self.T, self.sigma, 0.02)
        self.assertGreater(lo["n_flagged"], 0)
        self.assertEqual(lo["worst_strike"], self.K[i])
        self.assertIn(self.K[i], lo["flagged_strikes"])

    def test_gate_reports_act2_alongside(self):
        sh = detector.split_half(self.K, self.R, self.mid, self.hs, self.F0, self.pl.D, self.T, self.sigma, 0.02, self.edges, self.nuts, sampler="laplace", cutoff=3.0)
        a2 = detector.act2_signal(sh["halves"][0]["mean"] + 0.05, sh["halves"][0]["mean"], len(self.K))
        self.assertTrue(a2["fired"])
        g = detector.gate(sh, None, a2)
        self.assertEqual(g["act2_cents"], a2["cents"])
        self.assertFalse(g["fired"])   # Act II is reported, not gating


if __name__ == "__main__":
    unittest.main()
