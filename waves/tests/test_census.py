"""python3 -m unittest discover -s waves/tests -v"""
import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ladder import store  # noqa: E402
from waves import census  # noqa: E402

T0 = 1_700_000_000


def candles(rows):
    recs = []
    for ts, tk, b, a in rows:
        recs.append(dict(ts=ts, ticker=tk, volume=0.0, open_interest=1.0, yes_bid_open=b, yes_bid_high=b, yes_bid_low=b, yes_bid_close=b,
                         yes_ask_open=a, yes_ask_high=a, yes_ask_low=a, yes_ask_close=a))
    return pd.DataFrame(recs)


def info():
    return dict(series="S", event="E", kind="cumul", orient="greater", tickers=["A", "B", "C"], strikes=[1.0, 2.0, 3.0], close_epoch=None)


class TestCensus(unittest.TestCase):
    def test_event_and_response(self):
        rng = np.random.default_rng(1)
        rows = []
        # A: 200 small +-1c changes, then one +10c jump at minute 300; B follows +5c at 303; C never moves
        mid_a = 50.0
        for t in range(0, 300):
            if t % 1 == 0:
                mid_a += rng.choice([-1.0, 1.0])
                rows.append((T0 + 60 * t, "A", mid_a - 1, mid_a + 1))
        rows.append((T0 + 60 * 300, "A", mid_a + 9, mid_a + 11))
        rows.append((T0 + 60 * 340, "A", mid_a + 9, mid_a + 11))
        mid_b = 40.0
        for t in range(0, 300, 3):
            mid_b += rng.choice([-1.0, 1.0])
            rows.append((T0 + 60 * t, "B", mid_b - 1, mid_b + 1))
        rows.append((T0 + 60 * 303, "B", mid_b + 4, mid_b + 6))
        rows.append((T0, "C", 29, 31)); rows.append((T0 + 60 * 340, "C", 29, 31))
        g = store.build_grid(candles(rows), info())
        s, df = census.census(g, min_changes=50, sub=1)
        self.assertGreater(s["events_90"], 0)
        big = df[(df.i == 0) & (df.ts == T0 + 60 * 300)]
        self.assertEqual(len(big), 1)
        e = big.iloc[0]
        self.assertEqual(e.band, 99.9)          # a 10c jump among 1c changes is the top band
        self.assertEqual(e["first_+1"], 3)      # B first moved 3 minutes later
        self.assertAlmostEqual(e["resp_+1_5"], 0.5, places=5)  # +5 / +10
        self.assertAlmostEqual(e["resp_+1_0"], 0.0, places=5)
        self.assertEqual(e["first_+2"], 99)     # C never moved
        self.assertAlmostEqual(e["ret_5"], 1.0, places=5)      # A held its move
        self.assertEqual(e["first_-1"], -1)     # no bracket below A
        self.assertFalse(e.fallback)
        # B has 100 changes >= 50 -> own thresholds; C has 0 -> fallback (but never moves so no events)
        self.assertEqual(s["brackets_own"], 2)

    def test_skip_when_too_few_changes(self):
        rows = [(T0, "A", 49, 51), (T0 + 60, "A", 50, 52), (T0, "B", 39, 41), (T0, "C", 29, 31), (T0 + 120, "C", 29, 31)]
        g = store.build_grid(candles(rows), info())
        s, df = census.census(g, min_changes=50)
        self.assertIn("skipped", s); self.assertTrue(df.empty)


if __name__ == "__main__":
    unittest.main()
