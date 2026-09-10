"""Shared helpers for the unit tests: fixture loading and a scripted fake fetch."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import kalshi_common as kc  # noqa: E402
import logging  # noqa: E402
logging.getLogger("nightking").setLevel(logging.CRITICAL)   # keep unit-test output readable


def fixture(name: str) -> Any:
    with open(HERE / "fixtures" / name, "r", encoding="utf-8") as f:
        return json.load(f)


class FakeFetch:
    """Scripted transport for kalshi_common.Client. Rules are (regex, [responses]);
    each matching call pops the next response (the last one repeats)."""

    def __init__(self, rules: List[Tuple[str, List[Any]]]):
        self.rules = [(re.compile(p), list(rs)) for p, rs in rules]
        self.calls: List[str] = []

    def __call__(self, url: str) -> kc.Resp:
        self.calls.append(url)
        for rx, rs in self.rules:
            if rx.search(url):
                r = rs.pop(0) if len(rs) > 1 else rs[0]
                if isinstance(r, kc.Resp):
                    return r
                status, body = r
                if isinstance(body, (dict, list)):
                    return kc.Resp(status, body, json.dumps(body), {}, url)
                return kc.Resp(status, None, str(body or ""), {}, url)
        return kc.Resp(404, {"error": "no rule for %s" % url}, "no rule", {}, url)


def client_with(rules: List[Tuple[str, List[Any]]], pause: float = 0.0) -> Tuple[kc.Client, FakeFetch]:
    ff = FakeFetch(rules)
    c = kc.Client(live_base="https://live.test/trade-api/v2",
                  hist_base="https://hist.test/trade-api/v2/historical",
                  pause=pause, fetch=ff, retries=3)
    return c, ff


def ok(body: Any) -> Tuple[int, Any]:
    return (200, body)
