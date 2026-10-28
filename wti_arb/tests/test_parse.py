"""*_dollars parsing, cents normalisation, candle frames. These encode the
silent failure #2 from the brief: reading block['close'] returned None for
every row and the store filled with nulls."""
import unittest

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import fixture, kc


class TestCents(unittest.TestCase):
    def test_table(self):
        self.assertEqual(kc.cents("0.0100", dollars=True), 1.0)
        self.assertEqual(kc.cents("0.9700", dollars=True), 97.0)
        self.assertEqual(kc.cents("1.0000", dollars=True), 100.0)
        self.assertEqual(kc.cents(7, dollars=False), 7.0)
        self.assertEqual(kc.cents("7", dollars=False), 7.0)
        self.assertIsNone(kc.cents(None, dollars=True))
        self.assertIsNone(kc.cents("", dollars=True))
        self.assertIsNone(kc.cents("abc", dollars=True))
        self.assertIsNone(kc.cents(float("nan"), dollars=False))

    def test_to_float(self):
        self.assertEqual(kc.to_float("69.23"), 69.23)
        self.assertIsNone(kc.to_float(""))
        self.assertIsNone(kc.to_float(None))
        self.assertEqual(kc.to_float(3), 3.0)


class TestCandleDollars(unittest.TestCase):
    def setUp(self):
        self.c = fixture("candle_dollars.json")

    def test_field_style(self):
        self.assertEqual(kc.candle_field_style(self.c), "dollars")

    def test_row_matches_brief(self):
        r = kc.candle_row(self.c)
        self.assertEqual(r["ts"], 1787961600)
        self.assertEqual(r["yes_bid_open"], 1.0)
        self.assertEqual(r["yes_bid_high"], 3.0)
        self.assertEqual(r["yes_bid_low"], 0.0)
        self.assertEqual(r["yes_bid_close"], 2.0)
        self.assertEqual(r["yes_ask_open"], 97.0)
        self.assertEqual(r["yes_ask_close"], 4.0)
        self.assertEqual(r["volume"], 0.0)
        self.assertEqual(r["open_interest"], 0.0)
        # price block is {} when nothing traded -> None, never 0
        for k in ("price_open", "price_high", "price_low", "price_close"):
            self.assertIsNone(r[k])

    def test_bid_and_ask_never_both_null(self):
        """The regression: a parser that reads 'close' instead of 'close_dollars'."""
        r = kc.candle_row(self.c)
        self.assertIsNotNone(r["yes_bid_close"])
        self.assertIsNotNone(r["yes_ask_close"])

    def test_frame(self):
        df = kc.candles_to_frame([self.c, dict(self.c)], "KXWTIW", "KXWTIW-26AUG2814",
                                 "KXWTIW-26AUG2814-B70.50", "$70.00 to $70.99", "RANGE", 1, "live")
        self.assertEqual(len(df), 1, "duplicate ts must collapse")
        self.assertEqual(list(df.columns), kc.CANDLE_COLUMNS)
        self.assertEqual(df["spread"].iloc[0], 2.0)
        self.assertEqual(df["half_spread"].iloc[0], 1.0)
        self.assertEqual(str(df["ts"].dtype), "int64")
        self.assertEqual(str(df["yes_bid_close"].dtype), "float64")
        self.assertEqual(str(df["dt"].dtype), "datetime64[ns, UTC]")
        self.assertEqual(df["source"].iloc[0], "live")
        self.assertEqual(df["period_min"].iloc[0], 1)

    def test_duplicate_timestamp_is_dropped_and_counted(self):
        a = dict(self.c)
        b = dict(self.c, yes_bid={"close_dollars": "0.0300"})       # same ts, later, differs
        df = kc.candles_to_frame([a, b, dict(self.c, end_period_ts=1787961660)],
                                 "S", "E", "T", "b", "RANGE", 1, "live")
        self.assertEqual(len(df), 2)
        self.assertEqual(df.attrs["dupes_dropped"], 1)
        self.assertEqual(df.attrs["raw_candles"], 3)
        self.assertEqual(df["yes_bid_close"].iloc[0], 3.0, "last occurrence wins")

    def test_frame_drops_rows_without_ts(self):
        bad = dict(self.c)
        bad.pop("end_period_ts")
        df = kc.candles_to_frame([self.c, bad], "S", "E", "T", "b", "RANGE", 1, "live")
        self.assertEqual(len(df), 1)

    def test_empty_frame_has_schema(self):
        df = kc.candles_to_frame([], "S", "E", "T", "b", "RANGE", 1, "live")
        self.assertEqual(list(df.columns), kc.CANDLE_COLUMNS)
        self.assertEqual(len(df), 0)


class TestCandleHistoricalBare(unittest.TestCase):
    """The historical host: bare keys, decimal-DOLLAR strings. Captured from
    WTI-22OCT10-B89.495. Treating these as cents stored 58.9M candles 100x too small."""

    def setUp(self):
        self.c = fixture("candle_hist_bare.json")

    def test_style(self):
        self.assertEqual(kc.candle_field_style(self.c), "dollars_bare")

    def test_bare_dollar_strings_are_scaled_to_cents(self):
        r = kc.candle_row(self.c)
        self.assertEqual(r["yes_bid_close"], 4.0)
        self.assertEqual(r["yes_bid_low"], 3.0)
        self.assertEqual(r["yes_ask_close"], 7.0)
        self.assertEqual(r["yes_ask_high"], 100.0)
        self.assertIsNone(r["price_close"])
        self.assertEqual(r["volume"], 0.0)
        self.assertEqual(r["open_interest"], 0.0)

    def test_bare_int_is_still_cents(self):
        self.assertEqual(kc.ohlc({"close": 7}, "x")["x_close"], 7.0)
        self.assertEqual(kc.ohlc({"close": "0.0700"}, "x")["x_close"], 7.0)
        self.assertEqual(kc.ohlc({"close": 7.0}, "x")["x_close"], 7.0)


class TestCandleCentsLegacy(unittest.TestCase):
    def test_legacy_integer_cents(self):
        c = fixture("candle_cents.json")
        self.assertEqual(kc.candle_field_style(c), "cents")
        r = kc.candle_row(c)
        self.assertEqual(r["yes_bid_close"], 13.0)
        self.assertEqual(r["yes_ask_close"], 15.0)
        self.assertEqual(r["price_close"], 14.0)
        self.assertEqual(r["volume"], 42.0)
        self.assertEqual(r["open_interest"], 100.0)

    def test_dollars_take_precedence_when_both_present(self):
        blk = {"close": 13, "close_dollars": "0.1400"}
        self.assertEqual(kc.ohlc(blk, "x")["x_close"], 14.0)

    def test_unknown_shapes(self):
        self.assertEqual(kc.candle_field_style({"yes_bid": {}, "price": {}}), "unknown")
        self.assertEqual(kc.ohlc(None, "p"), {"p_open": None, "p_high": None, "p_low": None, "p_close": None})


if __name__ == "__main__":
    unittest.main()
