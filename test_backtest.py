"""Unit tests for synth/backtest.py on synthetic inputs. Nothing here opens the Kalshi store.

    python3 -m unittest test_backtest
"""
import os
import unittest

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from synth import act3, backtest as bt, black76  # noqa: E402


class TestEdges(unittest.TestCase):
    def test_between_greater_less(self):
        self.assertEqual(bt.market_edges("between", 84.00, 84.99), (83.995, 84.995))
        lo, hi = bt.market_edges("greater", 95.99, None)
        self.assertAlmostEqual(lo, 95.995)
        self.assertTrue(np.isinf(hi))
        lo, hi = bt.market_edges("less", None, 80.00)
        self.assertTrue(np.isinf(lo))
        self.assertAlmostEqual(hi, 79.995)
        with self.assertRaises(ValueError):
            bt.market_edges("between", None, 84.99)

    def test_subtitle_agrees_with_fields(self):
        self.assertEqual(bt.edges_from_subtitle("$84.00 to $84.99"), bt.market_edges("between", 84.00, 84.99))
        a = bt.edges_from_subtitle("Above $95.99")
        self.assertAlmostEqual(a[0], 95.995)
        b = bt.edges_from_subtitle("$79.99 or below")
        self.assertAlmostEqual(b[1], 79.995)
        self.assertIsNone(bt.edges_from_subtitle("Yes"))

    def test_ladder_is_contiguous(self):
        e1 = bt.market_edges("between", 84.00, 84.99)
        e2 = bt.market_edges("between", 85.00, 85.99)
        self.assertAlmostEqual(e1[1], e2[0])


class TestCondor(unittest.TestCase):
    def test_strikes_and_payoff(self):
        lo, hi = bt.market_edges("between", 84.00, 84.99)
        ks = bt.condor_strikes(lo, hi)
        self.assertEqual(ks, [83.5, 84.0, 85.0, 85.5])
        pay = bt.condor_payoff(np.array([83.0, 83.5, 83.75, 84.0, 84.5, 85.0, 85.25, 85.5, 86.0]), ks)
        np.testing.assert_allclose(pay, [0, 0, 0.25, 0.5, 0.5, 0.5, 0.25, 0, 0])
        # inside the bracket the structure pays exactly SPREAD_WIDTH -> one standard contract hedges 500 Kalshi contracts
        self.assertEqual(bt.SPREAD_WIDTH * bt.BBL["CL"], 500)
        self.assertEqual(bt.SPREAD_WIDTH * bt.BBL["MCO"], 50)

    def test_shift_moves_a_spread_outward(self):
        lo, hi = bt.market_edges("between", 84.00, 84.99)
        self.assertEqual(bt.condor_strikes(lo, hi, 1, 0), [83.25, 83.75, 85.0, 85.5])
        self.assertEqual(bt.condor_strikes(lo, hi, 0, 2), [83.5, 84.0, 85.5, 86.0])

    def test_structure_quotes_parity_converted(self):
        F0, D = 84.3, 1.0
        rows = []
        for k in (83.5, 84.0, 85.0, 85.5):
            for right in ("C", "P"):
                c = max(F0 - k, 0) + 0.40 if right == "C" else max(k - F0, 0) + 0.40   # a flat 40c time value, parity-consistent
                rows.append({"strike": k, "right": right, "bid_px_00": c - 0.01, "ask_px_00": c + 0.01, "age_min": 1.0})
        q = pd.DataFrame(rows)
        st = bt.structure_quotes(q, [83.5, 84.0, 85.0, 85.5], F0, D)
        self.assertIsNotNone(st)
        rights = [l["right"] for l in st["legs"]]
        self.assertEqual(rights, ["P", "P", "C", "C"])          # OTM side of each strike
        calls_only = bt.structure_quotes(q[q.right == "C"], [83.5, 84.0, 85.0, 85.5], F0, D)
        self.assertAlmostEqual(st["mid"], calls_only["mid"], places=9)
        self.assertAlmostEqual(st["sum_hs"], 0.04)
        self.assertGreater(st["buy"], st["sell"])
        self.assertAlmostEqual(st["buy"] - st["sell"], 2 * st["sum_hs"])

    def test_find_structure_shifts_when_a_leg_is_missing(self):
        F0, D = 84.3, 1.0
        rows = [{"strike": k, "right": "C", "bid_px_00": 0.1, "ask_px_00": 0.12, "age_min": 1.0} for k in (83.25, 83.75, 85.0, 85.5)]
        q = pd.DataFrame(rows)
        st, spec, shifts = bt.find_structure(q, 83.995, 84.995, F0, D)
        self.assertIsNotNone(st)
        self.assertEqual(spec["strikes"], [83.25, 83.75, 85.0, 85.5])
        self.assertEqual(shifts, (1, 0))
        st2, _, _ = bt.find_structure(q.iloc[:2], 83.995, 84.995, F0, D)
        self.assertIsNone(st2)

    def test_tails_are_two_leg_spreads_with_the_ramp_outside(self):
        up = bt.structure_spec(95.995, np.inf)              # 'Above $95.99': S >= 96
        self.assertEqual(up["strikes"], [95.5, 96.0])
        self.assertEqual(up["k0"], 0.0)
        np.testing.assert_allclose(bt.condor_payoff([95.0, 95.75, 96.0, 99.0], up), [0, 0.25, 0.5, 0.5])
        dn = bt.structure_spec(-np.inf, 84.995)             # '$84.99 or below': S <= 84.99
        self.assertEqual(dn["strikes"], [85.0, 85.5])
        self.assertEqual(dn["k0"], bt.SPREAD_WIDTH)
        np.testing.assert_allclose(bt.condor_payoff([80.0, 84.99, 85.25, 85.5, 90.0], dn), [0.5, 0.5, 0.25, 0, 0])
        rows = [{"strike": k, "right": "C", "bid_px_00": c - 0.01, "ask_px_00": c + 0.01, "age_min": 1.0} for k, c in ((85.0, 1.30), (85.5, 1.05))]
        st = bt.structure_quotes(pd.DataFrame(rows), dn, 86.0, 1.0)
        self.assertAlmostEqual(st["mid"], 0.5 - 0.25)         # 0.5 cash minus the 25c spread
        self.assertAlmostEqual(st["digital_mid"], 0.5)

    def test_estimated_leg_half_spread_uses_the_nearest_quoted_strikes(self):
        K = np.array([83.0, 84.0, 86.0, 90.0])
        hs = np.array([0.01, 0.03, 0.05, 0.02])
        # within $1: 83.5 -> {83, 84}; 84.0 -> {83, 84}; 85.0 -> {84, 86}; 85.5 -> {86}
        self.assertAlmostEqual(bt.estimate_leg_hs(K, hs, [83.5, 84.0, 85.0, 85.5]), 0.02 + 0.02 + 0.04 + 0.05)
        self.assertIsNone(bt.estimate_leg_hs(K, hs, [95.0, 95.5]))


class TestFriction(unittest.TestCase):
    def test_arithmetic_of_protocol_section_4(self):
        fr = bt.friction(0.10, 0.04)
        self.assertAlmostEqual(fr["kalshi_fee"], 0.0063)
        self.assertAlmostEqual(fr["cme_spread"], 0.08)
        self.assertAlmostEqual(fr["cme_fees"], 4 * 2.37 * 1.5 / 500)
        self.assertAlmostEqual(fr["total"], 0.0063 + 0.08 + 0.02844)
        self.assertAlmostEqual(bt.kalshi_fee(0.5), 0.0175)


class TestTrough(unittest.TestCase):
    def test_bimodal_has_one_trough_and_unimodal_none(self):
        s = np.linspace(80, 100, 801)
        f = np.exp(-0.5 * ((s - 86) / 1.5) ** 2) + 0.9 * np.exp(-0.5 * ((s - 94) / 1.5) ** 2)
        reg = bt.trough_regions(s, f)
        self.assertEqual(len(reg), 1)
        self.assertLess(reg[0][0], 90.0)
        self.assertGreater(reg[0][1], 90.0)
        self.assertTrue(bt.overlaps(89.995, 90.995, reg))
        self.assertFalse(bt.overlaps(85.995, 86.995, reg))
        self.assertEqual(bt.trough_regions(s, np.exp(-0.5 * ((s - 90) / 3) ** 2)), [])

    def test_small_ripple_is_ignored(self):
        s = np.linspace(80, 100, 801)
        f = np.exp(-0.5 * ((s - 90) / 3) ** 2) * (1 + 0.005 * np.sin(5 * s))
        self.assertEqual(bt.trough_regions(s, f), [])


class TestStage16And18(unittest.TestCase):
    def test_bracket_draws_sum_to_one_over_a_contiguous_ladder(self):
        F0, T, sigma, D = 85.0, 1 / 365.0, 0.5, 1.0
        K = np.arange(80.0, 90.5, 0.5)
        right = np.where(K >= F0, "C", "P")
        mid = np.array([black76.price(F0, k, T, sigma, D, r) for k, r in zip(K, right)])
        hs = np.full(K.size, 0.01)
        act3.set_prior("gauss", 3.0, 48, hs_floor=0.01, hs_mode="max")
        m = act3.Model(K, right, mid, hs, F0, D, T, sigma, se_F0=0.02, martingale=True)
        psi = act3.map_estimate(m)
        thetas = np.vstack([m.theta_of(psi)] * 3)
        lo = np.array([-np.inf, 82.995, 83.995, 84.995, 85.995, 86.995])
        hi = np.array([82.995, 83.995, 84.995, 85.995, 86.995, np.inf])
        p = bt.bracket_draws(m, thetas, lo, hi)
        np.testing.assert_allclose(p.sum(axis=1), 1.0, atol=1e-9)
        ref = m.summarise(thetas, lo[1:])["bracket"]
        np.testing.assert_allclose(p, ref, atol=1e-9)
        self.assertGreater(p[0, 2], 0.15)   # the ATM $1 bracket carries real mass (sd of the planted density ~$2.2)

    def test_stage18_recovers_a_planted_shrinkage(self):
        rng = np.random.default_rng(0)
        pq = np.array([0.02, 0.05, 0.10, 0.20, 0.30, 0.20, 0.08, 0.03, 0.02])
        m = np.arange(-4.0, 5.0)
        logit = lambda p: np.log(p / (1 - p))  # noqa: E731
        pm = 1 / (1 + np.exp(-(0.1 + 0.7 * logit(pq) + 0.05 * m)))
        draws = np.clip(pq[None, :] * np.exp(0.02 * rng.standard_normal((200, pq.size))), 1e-4, 1)
        abc = bt.stage18(pm, draws, m)
        self.assertEqual(abc.shape, (200, 3))
        self.assertAlmostEqual(np.median(abc[:, 1]), 0.7, delta=0.05)
        self.assertAlmostEqual(np.median(abc[:, 2]), 0.05, delta=0.02)
        pooled = bt.stage18_pooled([(pm, draws, m), (pm, draws, m + 1.0)])
        self.assertAlmostEqual(np.median(pooled[:, 0]), 0.7, delta=0.05)
        self.assertIsNone(bt.stage18(pm[:3], draws[:, :3], m[:3]))


class TestContractCheck(unittest.TestCase):
    def test_calendar_fallback_caught_when_kalshi_settled_on_the_other_month(self):
        settles = {("2026-04-17", "CLK6"): 83.85, ("2026-04-17", "CLM6"): 82.59, ("2026-04-17", "CLN6"): 80.22}
        d = {"settle_date": "2026-04-17", "ice_settle": None, "contract_source": "calendar"}
        out = bt.contract_check(d, "CLM6", settles, {"2026-04-17": 83.85})
        self.assertTrue(out["mismatch"])
        self.assertIn("CLK6", out["reason"])
        ok = bt.contract_check(dict(d, ice_settle=82.59), "CLM6", settles, {})
        self.assertFalse(ok["mismatch"])
        anomaly = bt.contract_check(dict(d, ice_settle=76.05), "CLM6", settles, {})
        self.assertFalse(anomaly["mismatch"])
        self.assertTrue(anomaly["basis_anomaly"])
        self.assertIn("unverifiable", bt.contract_check(d, "CLM6", settles, {})["reason"])


class TestCompareBracket(unittest.TestCase):
    def _ctx(self, raw_q):
        s = np.linspace(80, 100, 401)
        f = np.exp(-0.5 * ((s - 90) / 2.0) ** 2)
        return {"F0": 90.0, "D": 1.0, "raw_q": raw_q, "S_T": 85.5, "ice_settle": 85.5, "grid_s": s, "f_mean": f,
                "chain_K": np.array([85.0, 86.0, 94.0]), "chain_hs": np.array([0.01, 0.01, 0.01]), "date_ok": True}

    def _bracket(self):
        return {"ticker": "X", "sub_title": "$85.00 to $85.99", "lo": 84.995, "hi": 85.995, "result": "yes", "mid_dollar": 85.495,
                "pq_mean": 0.03, "pq_q05": 0.025, "pq_q95": 0.035, "band90": 0.01, "pq_draws": np.full(10, 0.03, np.float32),
                "interior_minimum": False, "loo_near_edge": False, "kalshi": {"bid": 0.30, "ask": 0.32, "age_min": 0.0}}

    def test_stale_legs_are_not_executable_but_are_reported(self):
        rows = [{"strike": k, "right": "P", "bid_px_00": 0.50, "ask_px_00": 0.52, "age_min": age} for k, age in ((84.5, 30.0), (85.0, 30.0), (86.0, 30.0), (86.5, 30.0))]
        b = self._bracket()
        bt.compare_bracket(b, self._ctx(pd.DataFrame(rows)))
        self.assertEqual(b["side"], "sell_kalshi")           # Kalshi 30c vs Act III 3c
        self.assertEqual(b["status"], "cme_leg_unquoted")     # the only quotes are 30 minutes old
        self.assertIsNotNone(b["chain_digital_stale"])
        self.assertIsNone(b["pnl_per_contract"])
        self.assertTrue(b["would_clear_est"])                 # 27c gap against ~1c band + ~11c estimated friction
        for r in rows:
            r["age_min"] = 1.0
        b2 = self._bracket()
        bt.compare_bracket(b2, self._ctx(pd.DataFrame(rows)))
        self.assertEqual(b2["status"], "traded")
        self.assertAlmostEqual(b2["pnl_kalshi"], 0.30 - 1.0 - bt.kalshi_fee(0.30))   # sold at 30c, bracket settled yes
        self.assertTrue(b2["settled_yes"])

    def test_gated_date_keeps_the_gap_but_never_trades(self):
        b = self._bracket()
        ctx = self._ctx(pd.DataFrame([{"strike": k, "right": "P", "bid_px_00": 0.5, "ask_px_00": 0.52, "age_min": 1.0} for k in (84.5, 85.0, 86.0, 86.5)]))
        ctx["date_ok"] = False
        bt.compare_bracket(b, ctx)
        self.assertEqual(b["status"], "date_gated")
        self.assertAlmostEqual(b["g"], 0.27)


class TestKalshiBar(unittest.TestCase):
    def test_snapshot_bar_then_stale_limit(self):
        t_end = 1_700_000_000 - (1_700_000_000 % 60) + 60   # a whole minute
        c = pd.DataFrame({"ticker": ["A"] * 3, "ts": [t_end - 1200, t_end - 300, t_end], "bid": [0.10, 0.11, 0.12], "ask": [0.12, 0.13, 0.14],
                          "volume": [1, 2, 3], "open_interest": [100, 100, 100]})
        snap = pd.Timestamp(t_end - 30, unit="s", tz="UTC")             # inside the bar ending at t_end
        k = bt.kalshi_at(c, "A", snap)
        self.assertTrue(k["exact_bar"])
        self.assertAlmostEqual(k["ask"], 0.14)
        k2 = bt.kalshi_at(c.iloc[:2], "A", snap)                        # exact bar missing: the 5-minute-old one
        self.assertFalse(k2["exact_bar"])
        self.assertAlmostEqual(k2["age_min"], 5.0)
        self.assertIsNone(bt.kalshi_at(c.iloc[:1], "A", snap))          # 20 minutes old: no executable price
        self.assertIsNone(bt.kalshi_at(c, "B", snap))


if __name__ == "__main__":
    unittest.main()
