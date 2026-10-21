"""Phase 1 collector — keyless public market data only.

Two interleaved sweeps:

  touch   every 60s, all 52 ladder series, one request per series. Gives the
          touch and touch sizes for all ~1,240 open markets at 1-minute
          resolution. This is what PROTOCOL §4's designated-provider proxy keys
          on, since that proxy is defined on spread and min(bid_size, ask_size).

  depth   a continuous rolling sweep over every open market, full depth, no
          truncation. A full pass takes ~3-4 min at the configured rate, so
          each market is snapshotted every few minutes with its own timestamp.
          This is the data phase 2 needs for queue realism and cannot be
          reconstructed later.

Plus price_ranges per market per cycle (tick-change alarm, PROTOCOL §1) and an
/incentive_programs snapshot daily (LIP coverage change).

There is no authentication in this process and no code path to an order
endpoint. The order manager does not exist yet.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import signal
import sys
import time
from typing import Dict, List

from . import config, kapi, store

log = logging.getLogger("mm.collect")

_STOP = False


def _on_signal(signum, frame):
    global _STOP
    _STOP = True
    log.warning("signal %s received - finishing cycle and flushing", signum)


class Collector:
    def __init__(self, series: List[str], once: bool = False):
        self.series = series
        self.once = once
        self.touch_buf = store.Buffer(store.TOUCH, max_rows=50000, max_age_s=300)
        self.depth_buf = store.Buffer(store.DEPTH, max_rows=20000, max_age_s=300)
        self.pr_buf = store.Buffer(store.PRICE_RANGES, max_rows=50000, max_age_s=3600)
        self.tickers: List[tuple] = []          # [(series, ticker)] rolling depth order
        self.depth_cursor = 0
        self.last_incentive = 0.0
        self.sweeps = 0
        self.depth_passes = 0
        self.tick_alarm_seen = set()

    # -- touch ---------------------------------------------------------------
    def touch_sweep(self) -> int:
        ts = store.utcnow()
        tickers: List[tuple] = []
        n = 0
        for s in self.series:
            if _STOP:
                break
            try:
                ms = kapi.open_markets(s)
            except kapi.Transient:
                log.warning("touch sweep: %s transient, skipping this cycle", s)
                continue
            except Exception as e:
                log.error("touch sweep: %s failed: %s", s, e)
                continue
            if not ms:
                continue
            self.touch_buf.add(store.touch_rows(s, ms, ts))
            self.pr_buf.add(store.price_range_rows(ms, s, ts))
            self._check_tick(s, ms)
            tickers.extend((s, m["ticker"]) for m in ms if m.get("ticker"))
            n += len(ms)
        if tickers:
            # Refresh the rolling depth universe but keep our place in it, so a
            # universe change does not restart the pass and starve the tail.
            self.tickers = tickers
            if self.depth_cursor >= len(self.tickers):
                self.depth_cursor = 0
        self.sweeps += 1
        return n

    def _check_tick(self, series: str, markets: List[dict]) -> None:
        """PROTOCOL §1 standing monitor. Alarms once per (series, tick)."""
        for m in markets:
            pr = m.get("price_ranges") or m.get("price_range")
            tick = kapi.tick_from_price_ranges(pr)
            if tick is None:
                continue
            if abs(tick - config.TICK_CENTS_EXPECTED) > 1e-9:
                key = (series, tick)
                if key not in self.tick_alarm_seen:
                    self.tick_alarm_seen.add(key)
                    log.error("TICK ALARM %s %s tick=%.4fc expected %.4fc - "
                              "cent-denominated thresholds are invalid for this series",
                              series, m.get("ticker"), tick, config.TICK_CENTS_EXPECTED)

    # -- depth ---------------------------------------------------------------
    def depth_slice(self, deadline: float) -> int:
        """Walk the rolling depth universe until the deadline."""
        n = 0
        while self.tickers and time.time() < deadline and not _STOP:
            series, ticker = self.tickers[self.depth_cursor]
            try:
                raw = kapi.orderbook(ticker)
                self.depth_buf.add(store.depth_row(ticker, series, raw, store.utcnow()))
                n += 1
            except kapi.Transient:
                log.warning("depth: %s transient", ticker)
            except Exception as e:
                log.error("depth: %s failed: %s", ticker, e)
            self.depth_cursor += 1
            if self.depth_cursor >= len(self.tickers):
                self.depth_cursor = 0
                self.depth_passes += 1
                log.info("depth pass %d complete (%d markets)",
                         self.depth_passes, len(self.tickers))
                break
        return n

    # -- incentive -----------------------------------------------------------
    def incentive_snapshot(self) -> None:
        if time.time() - self.last_incentive < config.INCENTIVE_PERIOD_S:
            return
        try:
            progs = kapi.paged("/incentive_programs", "incentive_programs", limit=1000)
        except Exception as e:
            log.warning("incentive snapshot failed: %s", e)
            return
        self.last_incentive = time.time()
        if not progs:
            return
        import pandas as pd
        ts = store.utcnow()
        df = pd.DataFrame(progs)
        df["ts"] = ts
        store.write_atomic(df, store.INCENTIVE, ts)
        log.info("incentive snapshot: %d programs", len(progs))

    # -- loop ----------------------------------------------------------------
    def run(self) -> None:
        config.ensure_dirs()
        log.info("collector starting: %d series, depth=full/no-truncation, "
                 "touch period %ds, req pause %.2fs",
                 len(self.series), config.TOUCH_PERIOD_S, config.REQ_PAUSE_S)
        # Beat immediately at startup. Without this the heartbeat still names the
        # PREVIOUS pid for a whole cycle (~5 min) after a restart, so the watchdog
        # sees a dead pid, concludes "collector not running", and kickstarts a
        # process that is in fact healthy -- a restart loop. Measured in the
        # 2026-10-20 SIGSTOP drill: 02:47:36 restart, first cycle beat 02:52:36.
        self._heartbeat(0, 0)
        while not _STOP:
            cycle_start = time.time()
            if config.killed():
                log.error("KILL file present (%s) - collector halting", config.KILL_FILE)
                break

            n_touch = self.touch_sweep()
            self.incentive_snapshot()

            deadline = cycle_start + config.TOUCH_PERIOD_S
            n_depth = self.depth_slice(deadline)

            for b in (self.touch_buf, self.depth_buf, self.pr_buf):
                b.flush()
            self._heartbeat(n_touch, n_depth)

            log.info("cycle %d: touch=%d depth=%d cursor=%d/%d elapsed=%.1fs",
                     self.sweeps, n_touch, n_depth, self.depth_cursor,
                     len(self.tickers), time.time() - cycle_start)

            if self.once:
                break
            sleep = deadline - time.time()
            while sleep > 0 and not _STOP:
                time.sleep(min(sleep, 1.0))
                sleep = deadline - time.time()

        for b in (self.touch_buf, self.depth_buf, self.pr_buf):
            b.flush(force=True)
        log.info("collector stopped after %d cycles, %d depth passes",
                 self.sweeps, self.depth_passes)

    def _heartbeat(self, n_touch: int, n_depth: int) -> None:
        """Watchdog reads this. Staleness is the liveness signal."""
        hb = config.LOGS / "collector.heartbeat.json"
        tmp = config.LOGS / ".collector.heartbeat.tmp"
        payload = dict(
            ts=store.utcnow().isoformat(),
            epoch=time.time(),
            sweeps=self.sweeps,
            depth_passes=self.depth_passes,
            universe=len(self.tickers),
            depth_cursor=self.depth_cursor,
            last_touch_rows=n_touch,
            last_depth_rows=n_depth,
            pid=__import__("os").getpid(),
        )
        tmp.write_text(json.dumps(payload))
        import os as _os
        _os.replace(tmp, hb)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="phase 1 shadow collector (keyless)")
    ap.add_argument("--once", action="store_true", help="single cycle then exit")
    ap.add_argument("--series", nargs="*", default=None, help="override universe")
    ap.add_argument("--log", default=None)
    a = ap.parse_args(argv)

    config.ensure_dirs()
    kapi.setup_logging(a.log or (config.LOGS / "collector.log"))
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    series = a.series or config.COLLECT_UNIVERSE
    Collector(series, once=a.once).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
