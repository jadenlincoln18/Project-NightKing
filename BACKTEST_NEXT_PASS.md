# BACKTEST_NEXT_PASS — what the next pass should examine

Written after `FINDINGS_BACKTEST.md`, and kept out of it on purpose: nothing here was used to shape the result, and
nothing here is a claim. It is the list of questions the result leaves open, in the order they bear on whether the
strategy can exist at all.

1. **A replication of a $1 bracket that costs less than the gap.** The four-leg outer condor on the $0.50 grid costs
   7–30¢ per Kalshi dollar in crossed spreads; the gaps are a cent. Candidates to cost out, in order: (a) hedging a
   *run* of adjacent brackets as one wider digital, so two legs serve several Kalshi contracts; (b) hedging the
   tail markets only ("Above $X", "$Y or below"), which need two legs not four; (c) a delta hedge in the future
   instead of an option replication, accepting the gamma; (d) resting rather than crossing on the CME side, with a
   fill model that the stored TBBO cannot yet support. Each changes the ramp and the max loss; the two sizing rules
   still apply.

2. **Executable CME prices.** The TBBO cannot price a structure at an instant. `bbo-1m` (quoted ~$1,835 when it was
   declined) or `mbp-1` for the ~30 settlement windows would settle the friction question with real top-of-book at
   the snapshot minute instead of the chain-estimated 8¢ spread term. Cost-preflight it; the window is small.

3. **Kalshi's roll convention, verified from the ladder itself.** Three of 37 weeks had Kalshi settling on a
   different delivery month than the calendar rule assigned. The ex-post check caught them; a *pre* check would read
   the contract off the ladder's own centre (the brackets Kalshi lists around the current price) against the two
   candidate months' levels on the day the ladder was listed.

4. **Is the longshot structure a tick or a bias?** b ≈ 0.63 pooled, 0.68–0.71 above 5¢. The clean test is the
   maker side: resting bids at the density's fair value in the deep tail (0.6¢ fair, 1¢ minimum tick) are not
   possible on a 1¢ grid, so the question is whether any Kalshi market has brackets fair-valued between 2¢ and 10¢
   where a resting order at fair would be filled by takers paying one tick above. That is a fill-rate question, not a
   density question.

5. **T-4h versus T-1d on the same bracket.** Gap signs agree at chance (49%) across the four hours. Either the
   disagreements are noise, which the magnitudes suggest, or Kalshi's ladder re-prices intraday faster than one
   snapshot shows. A 1-minute time series of gap per bracket through the final session would tell which, and would
   also show how long any disagreement lives (fedarb's 20-minute half-life is the benchmark).

6. **The band on real chains.** 23% of two-sided brackets sit outside the 90% posterior band at T-1d with no evidence
   of venue disagreement; the synthetic study's 95–97% coverage does not carry to real quotes. The suspects are the
   ones already named — the tick-floor noise model and the trough blind spot — and this is the first real-world
   coverage number the project has; it belongs in the next harness revision, not in the backtest.

7. **KXWTI as an arm.** The daily series has no market open at T-1d and its T-4h chains are harder (§3 of the
   findings). Whether it adds anything depends on 1 and 2 first.

Not on the list, deliberately: any change to the extractor, the gates, the thresholds or the bar in response to these
numbers. The result stands as reported.
