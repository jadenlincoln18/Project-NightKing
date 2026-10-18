# What a follow-on study would need to test catchability

Written after the census (`FINDINGS_WAVES.md`); kept separate from it. Nothing here is a claim that
anything is catchable.

1. **The near-expiry late leg against the underlying.** In the last 24 hours of a ladder's life the
   neighbours add 0.1-0.2 of the impulse over the following 30 minutes while the initiator holds.
   The first test is whether that is propagation or the underlying trending: align KXBRENTD /
   KXGOLDD / KXNATGASD / KXWTI events with the Pyth / ICE price path at one-minute resolution
   (free for Pyth; the CME intraday bars already bought cover WTI) and ask whether the neighbours'
   late move is explained by the underlying's move over the same 30 minutes. If it is, there is no
   wave to catch, only a trend. If it is not, the late leg is a ladder-internal lag and is worth a
   fill study.
2. **Sub-minute timing on the daily ladders.** Away from expiry the whole response is inside the
   candle. A websocket orderbook-delta subscription on four daily series (KXNATGASD, KXGOLDD,
   KXSILVERD, KXBRENTD) for two weeks would give the lag in seconds between a bracket's re-quote
   and its neighbours', and whether it is one market maker's batch update (zero lag, nothing to
   catch) or distinct participants. Build it only if item 1 does not close the direction.
3. **Executable version of the late leg.** If item 1 survives: repeat the census on the touch
   (buy at the neighbour's ask after the impulse, mark at its bid 5/10/30 minutes later) net of
   the taker fee, with resting size from `ladder/collect_books.py`, restricted to the last 24
   hours and events >= p99. That is the first number with a sign.
4. **Trade-driven versus quote-driven initiators.** Trade-driven moves hold (retained ~1.0) and
   quote-driven ones revert more (0.64-0.70). Any catching rule needs the trade flag at the time,
   which the websocket trade feed gives and the candles give only after the minute closes.
5. **Non-commodity ladders.** The expanded store is the test of the brief's hypothesis that waves
   are largest where no underlying forces coherence; the section-6 category table is the place to
   read it, and the follow-on should take the categories with the largest after-same-minute
   response and the highest event rate per ladder-day.
