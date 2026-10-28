"""Unit tests for the ladder study on synthetic ladders. Run from the repo root:
    python3 -m unittest discover -s ladder/tests -v
"""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ladder import census, fees, maker, propagation, store  # noqa: E402


def candles(rows):
    """rows: (ts, ticker, bid, ask, bid_hi=None, ask_lo=None, vol=0)."""
    recs = []
    for r in rows:
        ts, tk, b, a = r[:4]
        bh = r[4] if len(r) > 4 and r[4] is not None else b
        al = r[5] if len(r) > 5 and r[5] is not None else a
        v = r[6] if len(r) > 6 else 0.0
        recs.append(dict(ts=ts, ticker=tk, volume=v, open_interest=10.0,
                         yes_bid_open=b, yes_bid_high=bh, yes_bid_low=b, yes_bid_close=b,
                         yes_ask_open=a, yes_ask_high=a, yes_ask_low=al, yes_ask_close=a))
    return pd.DataFrame(recs)


def info(kind="cumul", orient="greater", tickers=("A", "B", "C"), strikes=(1.0, 2.0, 3.0), close=None):
    return dict(series="S", event="E", kind=kind, orient=orient, tickers=list(tickers), strikes=list(strikes), close_epoch=close)


T0 = 1_700_000_000


class TestGrid(unittest.TestCase):
    def test_ffill_and_empty_sides(self):
        c = candles([(T0, "A", 60, 62), (T0 + 120, "A", 0, 62), (T0 + 240, "A", 58, 100),
                     (T0, "B", 40, 42), (T0 + 240, "B", 41, 43),
                     (T0, "C", 20, 22), (T0 + 240, "C", 20, 22)])
        g = store.build_grid(c, info())
        self.assertEqual(g.shape, (5, 3))
        np.testing.assert_array_equal(g.bid[:, 0], [60, 60, np.nan, np.nan, 58])  # bid=0 -> no bid, carried
        np.testing.assert_array_equal(g.ask[:, 0], [62, 62, 62, 62, np.nan])     # ask=100 -> no ask
        np.testing.assert_array_equal(g.bid[:, 1], [40, 40, 40, 40, 41])
        self.assertTrue(g.has[0, 0] and not g.has[1, 0] and g.has[4, 2])
        self.assertTrue(np.isnan(g.bid_hi[1, 0]))  # intra-minute extremes only on candle minutes

    def test_less_orientation_flips(self):
        c = candles([(T0, "A", 10, 12), (T0, "B", 30, 34), (T0, "C", 70, 72)])
        g = store.build_grid(c, info(orient="less"))
        # P(<X) rising in X -> P(>X) falling in X; bid' = 100 - ask, ask' = 100 - bid
        np.testing.assert_array_equal(g.bid[0], [88, 66, 28])
        np.testing.assert_array_equal(g.ask[0], [90, 70, 30])

    def test_classify(self):
        m = pd.DataFrame(dict(ticker=["t1", "t2", "t3"], event_ticker=["E"] * 3, series=["S"] * 3,
                              strike_type=["greater"] * 3, floor_strike=[3.0, 1.0, 2.0], cap_strike=[np.nan] * 3,
                              yes_sub_title=[""] * 3, volume_fp=[1.0] * 3, open_interest_fp=[0.0] * 3, status=["x"] * 3,
                              result=[""] * 3, open_time_epoch=[1] * 3, close_time_epoch=[2] * 3,
                              expiration_time_epoch=[3] * 3, expiration_value_num=[np.nan] * 3))
        ev = store.events_table(m)
        self.assertEqual(ev.iloc[0].kind, "cumul")
        self.assertEqual(ev.iloc[0].tickers, ["t2", "t3", "t1"])
        m2 = m.copy(); m2.loc[0, "strike_type"] = "less"; m2.loc[0, "cap_strike"] = 0.5; m2.loc[0, "floor_strike"] = np.nan
        m2.loc[1, "strike_type"] = "between"; m2.loc[1, "cap_strike"] = 1.99
        ev2 = store.events_table(m2)
        self.assertEqual(ev2.iloc[0].kind, "range")
        self.assertEqual(ev2.iloc[0].tickers, ["t1", "t2", "t3"])


class TestTitleFallback(unittest.TestCase):
    def test_fill(self):
        g = pd.DataFrame(dict(strike_type=[None, None, None, "greater"], floor_strike=[np.nan] * 3 + [5.0], cap_strike=[np.nan] * 4,
                              yes_sub_title=["$77 to 77.99", "1624.99 or below", "Above 3.478", "x"]))
        f = store.fill_strike_from_title(g)
        self.assertEqual(f.strike_type.tolist(), ["between", "less", "greater", "greater"])
        self.assertEqual(f.floor_strike.tolist()[0], 77.0); self.assertEqual(f.cap_strike.tolist()[0], 77.99)
        self.assertEqual(f.cap_strike.tolist()[1], 1624.99); self.assertEqual(f.floor_strike.tolist()[2], 3.478)
        self.assertEqual(f.floor_strike.tolist()[3], 5.0)


class TestCensus(unittest.TestCase):
    def test_runs(self):
        s, l = census.runs_1d(np.array([0, 1, 1, 0, 1, 0, 0, 1], bool))
        np.testing.assert_array_equal(s, [1, 4, 7]); np.testing.assert_array_equal(l, [2, 1, 1])

    def test_violation_episode_and_net(self):
        # A (strike 1) ask 50; B (strike 2) bid 53 for 3 minutes -> edge 3c, then B drops to 49
        c = candles([(T0, "A", 48, 50), (T0, "B", 53, 55), (T0 + 180, "B", 49, 51), (T0, "C", 10, 12), (T0 + 180, "C", 10, 12)])
        g = store.build_grid(c, info())
        s, eps = census.cumul_census(g)
        self.assertEqual(s["viol_close_1c"], 3); self.assertEqual(s["viol_close_3c"], 3); self.assertEqual(s["viol_close_5c"], 0)
        self.assertEqual(len(eps), 1)
        e = eps.iloc[0]
        self.assertEqual(e.duration_min, 3); self.assertEqual(e.edge_max, 3.0); self.assertTrue(e.ended)
        self.assertAlmostEqual(e.net_start, 3.0 - fees.fee_cents(50) - fees.fee_cents(53), places=5)
        self.assertEqual(e.pair, 0); self.assertTrue(e.fresh_i and e.fresh_j); self.assertTrue(e.end_fresh_j and not e.end_fresh_i)
        self.assertEqual(s["viol_any_1c"], 3)

    def test_any_pair_beats_adjacent(self):
        # A ask 50, B 40/54, C bid 52 -> adjacent pairs fine (40-50, 52-54), but A-C violates by 2
        c = candles([(T0, "A", 48, 50), (T0, "B", 40, 54), (T0, "C", 52, 54)])
        g = store.build_grid(c, info())
        s, _ = census.cumul_census(g)
        self.assertEqual(s["viol_close_1c"], 0); self.assertEqual(s["viol_any_1c"], 1)

    def test_intra_is_upper_bound(self):
        c = candles([(T0, "A", 48, 50, 48, 47), (T0, "B", 46, 48, 49, 48), (T0, "C", 10, 12)])
        g = store.build_grid(c, info())
        s, _ = census.cumul_census(g)
        self.assertEqual(s["viol_close_1c"], 0); self.assertEqual(s["viol_intra_1c"], 1)  # 49 - 47 = 2 within the minute

    def test_range_sum(self):
        c = candles([(T0, "A", 30, 32), (T0, "B", 30, 32), (T0, "C", 30, 32)])  # asks sum 96 < 100
        g = store.build_grid(c, info(kind="range", orient=None))
        s, eps = census.range_census(g)
        self.assertEqual(s["buy_all_gross_minutes"], 1)
        # 4c gross minus 3 legs' fees (0.07*.32*.68*100 = 1.52c each, 4.57c) -> net negative, no episode
        self.assertEqual(s["buy_all_minutes"], 0)
        self.assertEqual(len(eps), 0)
        self.assertAlmostEqual(s["ask_excess_median"], -4.0)


class TestPropagation(unittest.TestCase):
    def test_lagged_neighbour(self):
        # A moves +4 at minute 1; B (stale at 1) follows +4 at minute 3 (itself an initiating move);
        # C is wide (spread 15c) so it is never a valid neighbour
        rows = [(T0, "A", 50, 52), (T0 + 60, "A", 54, 56), (T0, "B", 40, 42), (T0 + 180, "B", 44, 46), (T0, "C", 30, 45)]
        g = store.build_grid(candles(rows + [(T0 + 600, "C", 30, 45)]), info())
        acc, _ = propagation.impulse(g, thr=2.0)
        self.assertEqual(acc[("init", "body")], 2)
        key0 = (1, 0, "body", "body", True)
        self.assertIn(key0, acc); self.assertEqual(acc[key0][0], 1); self.assertAlmostEqual(acc[key0][1], 0.0)
        key5 = (1, 5, "body", "body", True)
        self.assertAlmostEqual(acc[key5][1] / acc[key5][3], 1.0)  # B caught up fully by h=5
        # stale trade: buy B at 42 at t, sell at 44 at t+5 -> +2 minus fees
        pnl = acc[key5][5] / acc[key5][4]
        self.assertAlmostEqual(pnl, 2.0 - fees.fee_cents(42) - fees.fee_cents(44), places=4)


class TestMaker(unittest.TestCase):
    def test_pava(self):
        np.testing.assert_allclose(maker.pava_decreasing([5, 3, 4, 1]), [5, 3.5, 3.5, 1])
        np.testing.assert_allclose(maker.pava_decreasing([3, 2, 1]), [3, 2, 1])

    def test_improvable(self):
        # mids 60, 65(!), 40 -> fit 62.5, 62.5, 40; bracket B bid 63 ask 67 -> fair 62.5 below bid: ask side room 4.5
        c = candles([(T0, "A", 58, 62), (T0, "B", 63, 67), (T0, "C", 38, 42)])
        g = store.build_grid(c, info())
        a = maker.maker_stats(g, every=1)
        self.assertEqual(a["minutes"], 1); self.assertEqual(a["nonmono_minutes"], 1)
        # A: fair 62.5 - bid 58 = 4.5 ; B: ask 67 - fair 62.5 = 4.5 ; C: fair 40, 2c room each side -> all three
        self.assertEqual(a["improvable"], 3); self.assertEqual(a["improvable_bid"], 2); self.assertEqual(a["improvable_ask"], 2)
        self.assertEqual(a["inside"], 1)  # A's fair (62.5) is above its ask, B's below its bid; only C is inside


class TestFees(unittest.TestCase):
    def test_fee(self):
        self.assertAlmostEqual(fees.fee_cents(50), 1.75)
        self.assertAlmostEqual(fees.fee_cents(50, contracts=1), 2.0)
        self.assertAlmostEqual(fees.fee_cents(50, contracts=100), 1.75)
        self.assertAlmostEqual(fees.fee_cents(5), 0.3325)
        self.assertAlmostEqual(fees.fee_cents(50, fees.MAKER), 0.4375)


if __name__ == "__main__":
    unittest.main()
