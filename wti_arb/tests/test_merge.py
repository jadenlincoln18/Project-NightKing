"""Live vs historical records: settlement fields must never be lost."""
import json
import unittest

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import fixture, kc


class TestMerge(unittest.TestCase):
    def test_hist_settlement_wins_over_empty_live(self):
        live, hist = fixture("market_live.json"), fixture("market_hist.json")
        m, meta = kc.merge_market(live, hist, "2026-09-01T00:00:00+00:00", "2026-09-01T00:00:01+00:00")
        self.assertEqual(m["expiration_value"], "69.23")
        self.assertEqual(m["result"], "no")
        self.assertEqual(m["settlement_ts"], "2026-06-26T18:31:02Z")
        self.assertEqual(m["status"], "settled")
        self.assertEqual(meta["primary_source"], "historical")
        self.assertEqual(meta["merge_conflicts"], [])
        self.assertTrue(meta["seen_live"] and meta["seen_hist"])
        # a field only the live record had is filled in
        self.assertEqual(m["yes_bid_dollars"], "0.0100")

    def test_live_settled_beats_stale_hist(self):
        hist = fixture("market_hist.json")
        stale = dict(hist, settlement_ts="", result="", status="closed")
        m, meta = kc.merge_market(hist, stale, "a", "b")
        self.assertEqual(meta["primary_source"], "live")
        self.assertEqual(m["settlement_ts"], hist["settlement_ts"])

    def test_conflict_recorded_primary_wins(self):
        hist = fixture("market_hist.json")
        live = dict(hist, floor_strike=84.0, status="finalized", settlement_ts="")
        m, meta = kc.merge_market(live, hist, "a", "b")
        self.assertEqual(meta["primary_source"], "historical")
        self.assertEqual(m["floor_strike"], 83.99)
        self.assertEqual(meta["merge_conflicts"], ["floor_strike"])

    def test_volatile_fields_are_not_conflicts(self):
        hist = fixture("market_hist.json")
        live = dict(hist, volume_fp="9999.00", status="finalized")
        _, meta = kc.merge_market(live, hist, "a", "b")
        self.assertEqual(meta["merge_conflicts"], [])

    def test_tie_goes_to_later_fetch(self):
        a = fixture("market_hist.json")
        b = dict(a, rules_primary="changed")
        _, meta = kc.merge_market(a, b, "2026-01-01T00:00:00", "2026-01-02T00:00:00")
        self.assertEqual(meta["primary_source"], "historical")
        _, meta2 = kc.merge_market(a, b, "2026-01-03T00:00:00", "2026-01-02T00:00:00")
        self.assertEqual(meta2["primary_source"], "live")

    def test_single_source(self):
        m, meta = kc.merge_market(None, fixture("market_hist.json"))
        self.assertEqual(meta["primary_source"], "historical")
        self.assertFalse(meta["seen_live"])
        m2, meta2 = kc.merge_market(fixture("market_live.json"), None)
        self.assertEqual(meta2["primary_source"], "live")
        self.assertEqual(kc.merge_market(None, None)[0], {})


class TestFlattenAndRow(unittest.TestCase):
    def test_flatten_keeps_every_scalar(self):
        m = fixture("market_hist.json")
        m["extra_new_field"] = "surprise"
        m["nested"] = {"a": 1}
        flat = kc.flatten_record(m)
        self.assertEqual(flat["extra_new_field"], "surprise")
        self.assertEqual(flat["custom_strike.front_month_contract"], "WBS 26V-ICE")
        self.assertEqual(flat["custom_strike.strike_date"], "2026-06-26T18:30:00Z")
        self.assertEqual(json.loads(flat["custom_strike_json"])["front_month_contract"], "WBS 26V-ICE")
        self.assertEqual(json.loads(flat["nested_json"]), {"a": 1})
        self.assertNotIn("custom_strike", flat)

    def test_market_row_and_frame(self):
        live, hist = fixture("market_live.json"), fixture("market_hist.json")
        m, meta = kc.merge_market(live, hist, "a", "b")
        ev = fixture("event_range.json")
        row = kc.market_row(m, meta, ev, "KXWTIW")
        self.assertEqual(row["settlement_source_name"], "ICE")
        self.assertEqual(row["mutually_exclusive"], True)
        self.assertEqual(row["ladder_kind"], "RANGE")
        self.assertEqual(row["expiration_value_num"], 69.23)
        self.assertEqual(row["settlement_ts_epoch"], kc.iso_to_epoch("2026-06-26T18:31:02Z"))
        self.assertEqual(row["ticker_format"], "new")
        self.assertEqual(row["ticker_hour"], 14)
        df = kc.markets_frame([row])
        for c in kc.MARKET_TYPED:
            self.assertIn(c, df.columns, c)
        self.assertEqual(str(df["floor_strike"].dtype), "float64")
        self.assertEqual(str(df["settlement_timer_seconds"].dtype), "Int64")
        self.assertEqual(str(df["mutually_exclusive"].dtype), "boolean")
        self.assertEqual(df["custom_strike.front_month_contract"].iloc[0], "WBS 26V-ICE")
        self.assertEqual(df["settlement_timer_seconds"].iloc[0], 3600)
        self.assertEqual(df["occurrence_datetime"].iloc[0], "2026-06-26T18:30:00Z")
        # untyped extra scalar survives as a string column
        self.assertIn("yes_bid_dollars", df.columns)

    def test_row_without_event_falls_back_to_labels(self):
        m = fixture("market_hist.json")
        row = kc.market_row(m, {"seen_live": False, "seen_hist": True, "primary_source": "historical",
                               "merge_conflicts": []}, None, "KXWTIW")
        self.assertIsNone(row["mutually_exclusive"])
        self.assertEqual(row["ladder_kind_source"], "labels")


if __name__ == "__main__":
    unittest.main()
