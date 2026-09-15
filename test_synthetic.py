#!/usr/bin/env python3
"""CI tests for the synthetic validation harness (synth/). Fast: the Laplace fallback
sampler stands in for NUTS everywhere except one 5-d Gaussian check of NUTS itself.

    python3 -m unittest test_synthetic -v        (~1 min)

These fail loudly on regressions in: planted densities (normalisation, martingale
mean, exact pricing against Black-76), the noise model (tick rounding, floor),
Stage 6 (forward recovery, outlier flagging), Black-76 inversion, Act II (lognormal
recovered to the cent, no-arbitrage checks), Act III (analytic gradient vs finite
differences, lognormal bracket recovery, martingale constraint, edge-mass check,
unconverged diagnostics), the geometry file (real strike grids spanning the gate to
the median), and the harness end to end including every injection switch.
"""

import os
import sys
import unittest

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

from synth import act2, act3, black76, densities, geometry, harness, noise, stage6  # noqa: E402

F0, SIGMA, T = 85.0, 0.6, 1.0 / 365.0


class TestPlanted(unittest.TestCase):
    def test_every_family_normalised_and_centred(self):
        for fam in densities.FAMILIES:
            pl = densities.Planted(fam, F0, SIGMA, T)
            self.assertAlmostEqual(float(pl.p.sum()), 1.0, places=10, msg=fam)
            self.assertAlmostEqual(pl.mean, F0, places=6, msg=fam)
            self.assertTrue(np.all(pl.f >= 0), fam)

    def test_lognormal_prices_match_black76(self):
        pl = densities.Planted("lognormal", F0, SIGMA, T)
        K = np.array([80.0, 83.5, 85.0, 86.25, 90.0])
        for right in ("C", "P"):
            exact = black76.price(F0, K, T, SIGMA, pl.D, right)
            got = pl.price(K, right)
            np.testing.assert_allclose(got, exact, atol=2e-5, err_msg=right)

    def test_bracket_probs_sum_to_one_and_match_cdf(self):
        pl = densities.Planted("crude_skew", F0, SIGMA, T)
        edges = densities.kalshi_edges(F0)
        p = pl.bracket_probs(edges)
        self.assertEqual(len(p), len(edges) + 1)
        self.assertAlmostEqual(float(p.sum()), 1.0, places=9)
        self.assertAlmostEqual(float(p[:5].sum()), float(pl.cdf(edges[4])), places=9)

    def test_bimodal_has_two_modes_and_spike_is_narrow(self):
        pl = densities.Planted("bimodal", F0, SIGMA, T)
        self.assertEqual(harness.count_modes(pl.s, pl.f), 2)
        self.assertEqual(harness.count_modes(pl.s, densities.Planted("lognormal", F0, SIGMA, T).f), 1)

    def test_kalshi_edges_are_dollar_thresholds(self):
        e = densities.kalshi_edges(87.3)
        self.assertAlmostEqual(e[1] - e[0], 1.0)
        self.assertTrue(np.all(np.isclose((e + 0.005) % 1.0, 0.0)))


class TestBlack76(unittest.TestCase):
    def test_round_trip_iv(self):
        K = np.array([78.0, 84.0, 85.0, 86.0, 95.0])
        sig = np.array([0.7, 0.62, 0.6, 0.61, 0.75])
        right = np.array(["P", "P", "C", "C", "C"])
        C = black76.price(F0, K, T, sig, 0.9999, right)
        iv = black76.implied_vol(C, F0, K, T, 0.9999, right)
        np.testing.assert_allclose(iv, sig, atol=1e-6)

    def test_below_intrinsic_is_nan(self):
        iv = black76.implied_vol(np.array([0.0, -0.01]), F0, np.array([80.0, 90.0]), T, 1.0, np.array(["C", "P"]))
        self.assertTrue(np.all(np.isnan(iv)))

    def test_vega_positive_and_largest_atm(self):
        K = np.array([75.0, 85.0, 95.0])
        v = black76.vega(F0, K, T, SIGMA)
        self.assertTrue(np.all(v > 0))
        self.assertEqual(int(np.argmax(v)), 1)


class TestNoise(unittest.TestCase):
    def test_quotes_on_tick_grid_with_bid_floor(self):
        rng = np.random.default_rng(0)
        true = np.array([0.0005, 0.02, 0.5, 3.0])
        hs = noise.half_spreads(rng, true, geometry.load()["half_spread_model"])
        bid, ask, mid, hsq = noise.quotes(rng, true, hs)
        self.assertTrue(np.all(bid >= 0.01 - 1e-12))
        self.assertTrue(np.all(ask > bid))
        np.testing.assert_allclose(bid, np.round(bid / 0.01) * 0.01, atol=1e-9)
        np.testing.assert_allclose(hsq, (ask - bid) / 2)

    def test_half_spread_widens_with_price_and_has_floor(self):
        rng = np.random.default_rng(1)
        m = geometry.load()["half_spread_model"]
        small = noise.half_spreads(rng, np.full(2000, 0.02), m)
        big = noise.half_spreads(rng, np.full(2000, 2.0), m)
        self.assertGreater(np.median(big), np.median(small))
        self.assertGreaterEqual(small.min(), 0.005 - 1e-12)

    def test_error_models(self):
        rng = np.random.default_rng(2)
        true = np.full(5000, 1.0)
        hs = np.full(5000, 0.05)
        _, _, mid_g, _ = noise.quotes(rng, true, hs, "gaussian")
        _, _, mid_u, _ = noise.quotes(rng, true, hs, "uniform")
        self.assertLess(abs(mid_g.std() - 0.05), 0.006)
        self.assertLess(abs(mid_u.std() - 0.05 / np.sqrt(3)), 0.006)
        _, _, mid_n, _ = noise.quotes(rng, true, hs, "none")
        np.testing.assert_allclose(mid_n, 1.0, atol=0.006)


class TestStage6(unittest.TestCase):
    def test_recovers_forward_and_discount(self):
        pl = densities.Planted("crude_skew", F0, SIGMA, T)
        K = np.arange(80.0, 90.01, 0.5)
        r = stage6.parity_forward(K, pl.price(K, "C"), pl.price(K, "P"))
        self.assertAlmostEqual(r["F0"], F0, places=4)
        self.assertAlmostEqual(r["D"], pl.D, places=4)

    def test_noisy_forward_within_se_and_outlier_flagged(self):
        rng = np.random.default_rng(3)
        pl = densities.Planted("lognormal", F0, SIGMA, T)
        K = np.arange(80.0, 90.01, 0.25)
        c = pl.price(K, "C") + rng.normal(0, 0.02, K.size)
        p = pl.price(K, "P") + rng.normal(0, 0.02, K.size)
        r = stage6.parity_forward(K, c, p)
        self.assertLess(abs(r["F0"] - F0), 4 * r["se_F0"] + 0.005)
        c[10] += 0.6  # one crossed quote
        r2 = stage6.parity_forward(K, c, p)
        self.assertTrue(r2["flagged"][10])
        self.assertLess(abs(r2["F0"] - F0), 4 * r2["se_F0"] + 0.005)


class TestActII(unittest.TestCase):
    def test_lognormal_recovered_to_the_cent(self):
        pl = densities.Planted("lognormal", F0, SIGMA, T)
        K = np.concatenate([np.arange(78.0, 85.0, 0.5), np.arange(85.0, 93.01, 0.5)])
        right = np.where(K < F0, "P", "C")
        mid = pl.price(K, right)
        hs = np.full(K.size, 0.01)
        edges = densities.kalshi_edges(F0)
        res = act2.run(K, right, mid, hs, F0, pl.D, T, edges, rng=np.random.default_rng(0))
        self.assertTrue(res["ok"])
        self.assertTrue(res["checks"]["density_nonneg"])
        self.assertTrue(res["checks"]["normalised"])
        self.assertLessEqual(res["svi"]["lee_slope"], 2.0 + 1e-9)
        self.assertLess(np.abs(res["bracket_probs"] - pl.bracket_probs(edges)).max(), 0.01)
        self.assertLess(abs(res["mean"] - F0), 0.05)

    def test_refuses_too_few_strikes(self):
        pl = densities.Planted("lognormal", F0, SIGMA, T)
        K = np.array([83.0, 84.0, 86.0])
        right = np.array(["P", "P", "C"])
        res = act2.run(K, right, pl.price(K, right), np.full(3, 0.01), F0, pl.D, T, densities.kalshi_edges(F0))
        self.assertFalse(res["ok"])


class TestActIII(unittest.TestCase):
    def _chain(self, family="lognormal", seed=0, n=24):
        rng = np.random.default_rng(seed)
        pl = densities.Planted(family, F0, SIGMA, T)
        K = np.linspace(F0 - 6, F0 + 7, n)
        right = np.where(K < F0, "P", "C")
        true = pl.price(K, right)
        hs = np.maximum(0.01 + 0.03 * true, 0.005)
        _, _, mid, hsq = noise.quotes(rng, true, hs)
        return pl, K, right, mid, hsq

    def test_gradient_matches_finite_differences(self):
        pl, K, right, mid, hs = self._chain()
        for mart in (True, False):
            mod = act3.Model(K, right, mid, hs, F0, pl.D, T, SIGMA, se_F0=0.01, martingale=mart)
            rng = np.random.default_rng(1)
            psi = rng.standard_normal(mod.dim) * 0.3
            lp, g = mod.logpost(psi)
            num = np.zeros_like(psi)
            for i in range(psi.size):
                e = np.zeros_like(psi)
                e[i] = 1e-5
                num[i] = (mod.logpost(psi + e, False) - mod.logpost(psi - e, False)) / 2e-5
            self.assertLess(np.max(np.abs(num - g) / (np.abs(g) + 1e-6)), 1e-4)

    def test_density_is_normalised_for_any_theta(self):
        pl, K, right, mid, hs = self._chain()
        mod = act3.Model(K, right, mid, hs, F0, pl.D, T, SIGMA)
        for th in (np.zeros(mod.m), np.random.default_rng(2).normal(0, 3, mod.m)):
            p, f = mod.density(th)
            self.assertAlmostEqual(float(p.sum()), 1.0, places=12)
            self.assertTrue(np.all(f > 0))

    def test_laplace_recovers_lognormal_brackets(self):
        pl, K, right, mid, hs = self._chain()
        mod = act3.Model(K, right, mid, hs, F0, pl.D, T, SIGMA, se_F0=0.01)
        res = act3.sample(mod, np.random.default_rng(0), sampler="laplace", n_chains=2, n_samples=300)
        edges = densities.kalshi_edges(F0)
        summ = mod.summarise(res["thetas"], edges)
        truth = pl.bracket_probs(edges)
        # the Gaussian approximation is a CI stand-in for NUTS: 1.5c on a lognormal is the sanity bar
        self.assertLess(np.abs(np.median(summ["bracket"], axis=0) - truth).max(), 0.015)
        self.assertLess(abs(summ["mean_F"].mean() - F0), 0.05)
        self.assertLess(summ["chi2"].mean() / len(K), 3.0)
        self.assertLess(summ["edge_mass"].mean(axis=0).max(), harness.EDGE_MASS_MAX)

    def test_martingale_constraint_pins_the_mean(self):
        pl, K, right, mid, hs = self._chain(seed=5)
        target = F0 + 0.30
        mod = act3.Model(K, right, mid, hs, target, pl.D, T, SIGMA, se_F0=0.01, martingale=True)
        psi = act3.map_estimate(mod)
        p, _ = mod.density(mod.theta_from(psi)[0])
        self.assertLess(abs(mod.mean(p) - target), 0.05)
        chi2_on = mod.chi2(mod.theta_from(psi)[0])[0]
        mod_off = act3.Model(K, right, mid, hs, target, pl.D, T, SIGMA, se_F0=0.01, martingale=False)
        chi2_off = mod_off.chi2(mod_off.theta_from(act3.map_estimate(mod_off))[0])[0]
        self.assertGreater(chi2_on, 2 * chi2_off)  # a 30c wrong forward fights the quotes

    def test_truncated_grid_leaks_mass_to_the_edges(self):
        pl, K, right, mid, hs = self._chain(family="crude_skew")
        mod = act3.Model(K, right, mid, hs, F0, pl.D, T, SIGMA, se_F0=0.01, extent_sd=1.5)
        psi = act3.map_estimate(mod)
        summ = mod.summarise(mod.theta_from(psi)[0][None, :], densities.kalshi_edges(F0))
        self.assertGreater(summ["edge_mass"].max(), harness.EDGE_MASS_MAX)

    def test_nuts_samples_a_gaussian(self):
        class G:
            dim = 5

            def logpost(self, q, with_grad=True):
                lp = -0.5 * float(q @ q)
                return (lp, -q) if with_grad else lp
        rng = np.random.default_rng(0)
        res = act3.NUTS(G(), rng).run(np.zeros(5), 200, 600)
        self.assertEqual(res["divergences"], 0)
        self.assertLess(np.abs(res["draws"].mean(axis=0)).max(), 0.2)
        self.assertLess(np.abs(res["draws"].std(axis=0) - 1).max(), 0.2)

    def test_short_chain_is_flagged(self):
        pl, K, right, mid, hs = self._chain()
        mod = act3.Model(K, right, mid, hs, F0, pl.D, T, SIGMA, se_F0=0.01)
        res = act3.sample(mod, np.random.default_rng(0), sampler="nuts", n_chains=2, n_warmup=5, n_samples=30)
        self.assertFalse(res["converged"])

    def test_rhat_and_ess_on_iid_draws(self):
        ch = np.random.default_rng(0).standard_normal((4, 500, 3))
        self.assertLess(act3.split_rhat(ch).max(), 1.02)
        self.assertGreater(act3.ess(ch).min(), 1200)


class TestGeometry(unittest.TestCase):
    def test_real_grids_span_gate_to_median(self):
        geo = geometry.load()
        snaps = geometry.snapshots(geo)  # both lookbacks, gate applied (8 strikes, 3 per wing)
        self.assertGreaterEqual(len(snaps), 100)
        counts = np.array([s["n_strikes"] for s in snaps])
        self.assertLessEqual(counts.min(), 15)   # thin real chains exist; the harness thins further to 8
        self.assertGreaterEqual(np.median(counts), 23)
        for s in snaps[:20]:
            K = np.array(s["strikes"])
            self.assertTrue(np.all(np.diff(K) > 0))
            self.assertTrue(np.all(np.isclose(K * 4, np.round(K * 4))), "strikes are on $0.25 increments")
            self.assertGreaterEqual(s["n_below"], 3)
            self.assertGreaterEqual(s["n_above"], 3)
        m = geo["half_spread_model"]
        self.assertGreater(m["beta"], 0.0)
        self.assertGreater(m["tau"], 0.0)

    def test_thinning_keeps_wings(self):
        rng = np.random.default_rng(0)
        K = np.arange(70.0, 100.0, 0.5)
        right = np.where(K < 85.0, "P", "C")
        Kt, Rt = harness.thin_strikes(rng, K, right, 85.0, 8)
        self.assertEqual(len(Kt), 8)
        self.assertGreaterEqual(int((Kt < 85.0).sum()), 3)
        self.assertGreaterEqual(int((Kt >= 85.0).sum()), 3)


class TestHarness(unittest.TestCase):
    def test_run_one_clean(self):
        r = harness.run_one({"family": "lognormal", "sampler": "laplace", "snapshot": 0}, seed=11)
        self.assertIsNotNone(r["act3_bracket_mean"])
        self.assertTrue(r["act2_ok"])
        self.assertLess(abs(r["forward_err_cents"]), 10.0)
        self.assertTrue(r["checks"]["normalisation_edge_mass_ok"])
        self.assertLess(r["checks"]["chi2_map_per_strike"], 3.0)
        self.assertEqual(len(r["p_true"]), len(r["edges"]) + 1)
        for L in (50, 80, 90, 95):
            self.assertEqual(len(r["act3_bracket_cov"][L]), len(r["p_true"]))

    def test_injections_are_detected(self):
        base = {"family": "crude_skew", "sampler": "laplace", "snapshot": 0}
        r = harness.run_one(dict(base, inject="convexity"), seed=12)
        self.assertTrue(r["inject_flagged_by_parity"] or abs(r["inject_resid_z"]) > 3)
        r = harness.run_one(dict(base, inject="stale"), seed=12)
        self.assertTrue(r["inject_flagged_by_parity"] or abs(r["inject_resid_z"]) > 3)
        r = harness.run_one(dict(base, extent_sd=1.5), seed=12)
        self.assertFalse(r["checks"]["normalisation_edge_mass_ok"])
        r = harness.run_one(dict(base, forward_offset=50), seed=12)
        self.assertGreater(abs(r["F0_used"] - r["F0_hat"]) / r["se_F0"], 3.0)
        self.assertGreater(r["checks"]["chi2_map_per_strike"], 2.0)
        r = harness.run_one(dict(base, inject="unconverged"), seed=12)
        self.assertFalse(r["checks"]["sampler_ok"])

    def test_no_martingale_mean_near_forward(self):
        r = harness.run_one({"family": "lognormal", "sampler": "laplace", "martingale": False, "snapshot": 0}, seed=13)
        self.assertLess(abs(r["checks"]["mean_vs_true_F_cents"]), 25.0)


if __name__ == "__main__":
    unittest.main()
