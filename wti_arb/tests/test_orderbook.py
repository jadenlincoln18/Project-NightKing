"""Kalshi books are bids only on both sides: yes_ask = 100 - no_bid."""
import unittest

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import fixture, kc


class TestBook(unittest.TestCase):
    def test_cents_shape(self):
        b = kc.book_from_kalshi(fixture("orderbook_cents.json"))
        self.assertEqual(b["yes_bids"], [(7.0, 50), (5.0, 100)])          # best bid first
        self.assertEqual(b["yes_asks"], [(7.0, 10), (10.0, 20)])          # 100-93, 100-90; sizes kept

    def test_fp_dollars_shape(self):
        b = kc.book_from_kalshi(fixture("orderbook_fp.json"))
        self.assertEqual(b["yes_bids"], [(7.0, 50), (5.0, 100)])
        self.assertEqual(b["yes_asks"], [(7.0, 10), (10.0, 20)])

    def test_raw_book_is_not_bid_ask(self):
        """Treating the 'no' side as yes asks at face value would give 90/93."""
        b = kc.book_from_kalshi(fixture("orderbook_cents.json"))
        self.assertNotIn((90.0, 20), b["yes_asks"])

    def test_empty_and_bad(self):
        self.assertEqual(kc.book_from_kalshi({}), {"yes_bids": [], "yes_asks": []})
        self.assertEqual(kc.book_from_kalshi(None), {"yes_bids": [], "yes_asks": []})
        b = kc.book_from_kalshi({"orderbook": {"yes": [["x", 1], [5, 0], [6]], "no": None}})
        self.assertEqual(b["yes_bids"], [])


if __name__ == "__main__":
    unittest.main()
