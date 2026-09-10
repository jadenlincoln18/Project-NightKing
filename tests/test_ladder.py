"""mutually_exclusive is definitive; label heuristics are only a fallback."""
import unittest

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import fixture, kc

RANGE_LABELS = ["Below $71.00", "$71.00 to $71.99", "$72.00 to $72.99", "$73.00 to $73.99", "Above $73.99"]
CUMUL_LABELS = ["Above $5.79", "Above $5.85", "Above $5.91", "Above $5.97", "Above $6.03"]
OR_ABOVE = ["75 or above", "80 or above", "85 or above", "90 or above"]
NAMES = ["Kevin Warsh", "John Williams", "Neel Kashkari"]


class TestLadderKind(unittest.TestCase):
    def test_flag_wins_over_labels(self):
        self.assertEqual(kc.ladder_kind(True, CUMUL_LABELS), ("RANGE", "mutually_exclusive"))
        self.assertEqual(kc.ladder_kind(False, RANGE_LABELS), ("CUMUL", "mutually_exclusive"))
        self.assertEqual(kc.ladder_kind("true", CUMUL_LABELS), ("RANGE", "mutually_exclusive"))

    def test_fallback_to_labels_when_missing(self):
        self.assertEqual(kc.ladder_kind(None, RANGE_LABELS), ("RANGE", "labels"))
        self.assertEqual(kc.ladder_kind(None, CUMUL_LABELS), ("CUMUL", "labels"))
        self.assertEqual(kc.ladder_kind(None, OR_ABOVE), ("CUMUL", "labels"))
        self.assertEqual(kc.ladder_kind(None, NAMES), ("OTHER", "labels"))
        self.assertEqual(kc.ladder_kind(None, []), ("UNKNOWN", "labels"))

    def test_fixture_events(self):
        rng = fixture("event_range.json")
        cum = fixture("event_cumul.json")
        self.assertEqual(kc.ladder_kind(rng["mutually_exclusive"])[0], "RANGE")
        self.assertEqual(kc.ladder_kind(cum["mutually_exclusive"])[0], "CUMUL")

    def test_events_frame(self):
        df = kc.events_frame([fixture("event_range.json"), fixture("event_cumul.json")], "X")
        self.assertEqual(list(df["ladder_kind"]), ["RANGE", "CUMUL"])
        self.assertEqual(list(df["ladder_kind_source"]), ["mutually_exclusive"] * 2)
        self.assertEqual(list(df["n_markets"]), [4, 3])
        self.assertEqual(df["settlement_source_name"].iloc[0], "ICE")
        self.assertIn("theice.com", df["settlement_source_url"].iloc[0])
        self.assertNotIn("markets_json", df.columns)
        self.assertEqual(str(df["mutually_exclusive"].dtype), "boolean")


class TestSettlementSources(unittest.TestCase):
    def test_join(self):
        n, u = kc.settlement_source_fields([{"name": "ICE", "url": "u1"}, {"name": "Pyth", "url": "u2"}])
        self.assertEqual(n, "ICE | Pyth")
        self.assertEqual(u, "u1 | u2")
        self.assertEqual(kc.settlement_source_fields([]), (None, None))
        self.assertEqual(kc.settlement_source_fields(None), (None, None))


if __name__ == "__main__":
    unittest.main()
