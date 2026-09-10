"""HTTP client behaviour with a scripted transport: retries, paging until the
cursor is empty, host fallback and the ok/empty/not_found/error classification."""
import unittest

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import kc, client_with, ok


def cs(n, start=1000):
    return {"candlesticks": [{"end_period_ts": start + 60 * i, "yes_bid": {"close_dollars": "0.10"},
                              "yes_ask": {"close_dollars": "0.12"}, "price": {}} for i in range(n)]}


class TestRetries(unittest.TestCase):
    def test_429_then_200(self):
        c, ff = client_with([(r"/x", [kc.Resp(429, None, "slow down", {"Retry-After": "0"}), ok({"a": 1})])])
        r = c.get("https://live.test/x")
        self.assertEqual(r.status, 200)
        self.assertEqual(len(ff.calls), 2)
        self.assertEqual(c.stats["throttled"], 1)
        self.assertEqual(c.stats.get("retries", 0), 0, "429 waits do not consume the 5xx budget")

    def test_5xx_then_200(self):
        c, ff = client_with([(r"/x", [(503, "down"), ok({"a": 1})])])
        c.retries = 3
        r = c.get("https://live.test/x")
        self.assertEqual(r.status, 200)

    def test_network_failure_exhausts(self):
        c, ff = client_with([(r"/x", [kc.Resp(0, None, "URLError: boom")])])
        r = c.get("https://live.test/x")
        self.assertEqual(r.status, 0)
        self.assertEqual(len(ff.calls), 3)

    def test_4xx_returns_immediately_with_body(self):
        c, ff = client_with([(r"/x", [(400, {"error": "max candlesticks: 5000"})])])
        r = c.get("https://live.test/x")
        self.assertEqual(r.status, 400)
        self.assertIn("max candlesticks", r.text)
        self.assertEqual(len(ff.calls), 1)


class TestPaging(unittest.TestCase):
    def test_pages_until_cursor_empty(self):
        pages = [ok({"markets": [{"ticker": "A%d" % i} for i in range(200)], "cursor": "c1"}),
                 ok({"markets": [{"ticker": "B%d" % i} for i in range(200)], "cursor": "c2"}),
                 ok({"markets": [{"ticker": "C"}], "cursor": ""})]
        c, ff = client_with([(r"/historical/markets", pages)])
        pr = c.markets_hist("KXWTI")
        self.assertEqual(len(pr.items), 401)
        self.assertEqual(pr.pages, 3)
        self.assertTrue(pr.ended_cleanly)
        self.assertFalse(pr.truncation_warning)
        self.assertIn("cursor=c1", ff.calls[1])
        self.assertIn("cursor=c2", ff.calls[2])

    def test_exact_multiple_flags_truncation(self):
        pages = [ok({"markets": [{"ticker": "A%d" % i} for i in range(200)], "cursor": ""})]
        c, _ = client_with([(r"/historical/markets", pages)])
        pr = c.markets_hist("KXWTI")
        self.assertTrue(pr.truncation_warning)
        self.assertTrue(pr.ended_cleanly)

    def test_no_page_cap(self):
        n = kc.PAGE_SOFT_ALARM + 5
        state = {"i": 0}

        def fetch(url):
            state["i"] += 1
            done = state["i"] >= n
            return kc.Resp(200, {"events": [{"event_ticker": "E%d" % state["i"]}],
                                 "cursor": "" if done else "c%d" % state["i"]}, "", {}, url)
        c = kc.Client(pause=0.0, fetch=fetch)
        pr = c.events("S", nested=False)
        self.assertEqual(pr.pages, n)
        self.assertEqual(len(pr.items), n)
        self.assertTrue(pr.ended_cleanly)

    def test_http_error_mid_paging_is_not_clean(self):
        pages = [ok({"events": [{"event_ticker": "E1"}], "cursor": "c1"}), (500, "boom")]
        c, _ = client_with([(r"/events", pages)])
        pr = c.events("S")
        self.assertFalse(pr.ended_cleanly)
        self.assertEqual(pr.last_status, 500)
        self.assertEqual(len(pr.items), 1)

    def test_repeated_cursor_guard(self):
        pages = [ok({"events": [{"event_ticker": "E1"}], "cursor": "same"})]
        c, ff = client_with([(r"/events", pages)])
        pr = c.events("S")
        self.assertFalse(pr.ended_cleanly)
        self.assertLessEqual(len(ff.calls), 3)


class TestClassification(unittest.TestCase):
    def test_live_ok(self):
        c, ff = client_with([(r"live.test.*candlesticks", [ok(cs(5))])])
        r = kc.fetch_market_candles(c, "S", "T", 0, 3600, 1)
        self.assertEqual((r.status, r.source, r.rows, r.http_live, r.http_hist), ("ok", "live", 5, 200, None))
        self.assertTrue(r.fetch_ok)
        self.assertEqual(len(r.raw), 1)

    def test_live_404_hist_200(self):
        c, ff = client_with([(r"live.test.*candlesticks", [(404, {"error": "not found"})]),
                             (r"hist.test.*candlesticks", [ok(cs(2))])])
        r = kc.fetch_market_candles(c, "S", "T", 0, 3600, 1)
        self.assertEqual((r.status, r.source, r.rows, r.http_live, r.http_hist), ("ok", "historical", 2, 404, 200))

    def test_404_both_is_not_found(self):
        c, _ = client_with([(r"candlesticks", [(404, {"error": "not found"})])])
        r = kc.fetch_market_candles(c, "S", "T", 0, 3600, 1)
        self.assertEqual(r.status, "not_found")
        self.assertTrue(r.fetch_ok, "a genuine 404 is a completed fetch, not a failure")
        self.assertEqual((r.http_live, r.http_hist), (404, 404))

    def test_200_empty_is_empty(self):
        c, _ = client_with([(r"live.test.*candlesticks", [ok({"candlesticks": []})])])
        r = kc.fetch_market_candles(c, "S", "T", 0, 3600, 1)
        self.assertEqual((r.status, r.rows), ("empty", 0))
        self.assertTrue(r.fetch_ok)

    def test_network_failure_is_error(self):
        c, _ = client_with([(r"candlesticks", [kc.Resp(0, None, "URLError")])])
        r = kc.fetch_market_candles(c, "S", "T", 0, 3600, 1)
        self.assertEqual(r.status, "error")
        self.assertFalse(r.fetch_ok)
        self.assertEqual((r.http_live, r.http_hist), (0, 0))
        self.assertIn("HTTP 0", r.error)

    def test_live_5xx_hist_404_is_error_not_not_found(self):
        c, _ = client_with([(r"live.test.*candlesticks", [(503, "down")]),
                            (r"hist.test.*candlesticks", [(404, "nf")])])
        r = kc.fetch_market_candles(c, "S", "T", 0, 3600, 1)
        self.assertEqual(r.status, "error")
        self.assertFalse(r.fetch_ok)

    def test_multi_chunk_joins(self):
        state = {"n": 0}

        def fetch(url):
            state["n"] += 1
            return kc.Resp(200, cs(3, 1000 * state["n"]), "", {}, url)
        c = kc.Client(pause=0.0, fetch=fetch)
        r = kc.fetch_market_candles(c, "S", "T", 0, 3 * 4999 * 60, 1, kc.CapHolder(5000))
        self.assertEqual(r.chunks, 3)
        self.assertEqual(r.requests, 3)
        self.assertEqual(r.rows, 9)


class TestRateLimiter(unittest.TestCase):
    def test_spacing(self):
        import time
        rl = kc.RateLimiter(0.02)
        t0 = time.monotonic()
        for _ in range(5):
            rl.wait()
        self.assertGreaterEqual(time.monotonic() - t0, 0.07)
        kc.RateLimiter(0).wait()


if __name__ == "__main__":
    unittest.main()
