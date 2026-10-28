# Ladder dynamics — what the next pass should examine

Written after the result (`FINDINGS_LADDER_DYNAMICS.md`), kept separate from it.

1. **Size the KXWTIW sell-every-bracket episodes against the live book.** The one
   region that clears fees. Keep `collect_books.py` running through at least two
   weekly expiries; for every live minute where sum(bids) > 100 + fees, record the
   thinnest tail bid's size and the number of brackets whose bid is the 1-2c
   floor. The answer is a size-weighted net per set and the capital it ties up
   (sum of 100 − bid per set). If the thinnest leg is routinely ≥ 100 contracts the
   trade exists at $100-300 per set per episode; if it is 1-5 contracts it does not.
2. **Simultaneity of 15-27 legs.** The sum episodes last a median 2 minutes. A
   fill study needs the websocket book (sub-second) on KXWTIW only, not the whole
   exchange. Extend the collector with a websocket subscription for one series
   before building anything else.
3. **Live shape violations with size.** The historical census has no depth. Run
   `report.live_violations` over the collected sweeps weekly; the first week found
   none during a Sunday session, which says nothing yet.
4. **Posting study (brief §5, scoped out here).** 58% of bracket-minutes have room
   for a one-tick improvement on the side away from the ladder's own monotone fit.
   The question that decides it is adverse selection: when a coherent quoter is
   best bid, how often is it lifted and what does the bracket do in the next 30
   minutes. That is a different design (fills, not prices) and needs the book.
5. **Yearly / monthly dead-market violations.** The large edges (20-80c, hours long)
   all sit in KXNGASMIN/MAX, KXAAAGASMAX*/MIN*, KXWTIMINM. Each is one resting
   order. A one-off live check of the current ones (size at the touch via the
   collector's depth files) costs nothing and either closes the class or finds a
   few hundred dollars.
6. **Fee verification.** Confirm the maker coefficient (0.0175 vs 0) on the
   commodity ladders from Kalshi's schedule once the PDF is reachable; only the
   section 5 number depends on it.
7. **Not worth doing:** the stale-neighbour propagation trade (negative at every
   horizon, every threshold, every series), finer candles (the API has none; the
   intra-minute upper bound already shows one-tick crossings), and any revisit of
   the CME leg.
