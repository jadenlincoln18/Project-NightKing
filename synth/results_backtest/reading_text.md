**What the gaps look like.** On every cleared date the picture is the same: the Kalshi ladder and the Act III density
agree bracket by bracket to about a cent. Across the 296 two-sided brackets at T-1d the mean gap is +0.2¢, the mean
|gap| 1.1¢, the median 0.5¢; 14 brackets (5%) are more than 5¢ apart and one more than 10¢. By moneyness the deep
tail runs +0.2¢ (Kalshi 2.1¢ against 1.5¢), the moderate tail +0.2¢, the body −0.6¢ on 22 brackets, the five
favourites −1.0¢. Per date, the mean tail gap is positive on 67% of dates with a mean of +0.3¢ and a standard
deviation across dates of 0.6¢ — a sign preference that is real and worth a quarter of a cent. T-4h is the same story
with smaller numbers (mean gap +0.0¢, mean |gap| 1.0¢, 9% outside the band). The posterior bands are narrow (0.7¢ in
the deep tail, 2.4¢ on the moderate tail, 4.7¢ in the body) and 23% of brackets sit outside them, which says the band
is a little tight on real chains, as the synthetic study predicted; it does not say the venues disagree.

**The structure, and why it is a cent.** Stage 18 is unambiguous in logit space: b = 0.69 pooled at T-1d, 0.68 at
T-4h, with 90% intervals a few hundredths wide, and 14 of the 24 dates with their own regression put b below 1 on
their own (the per-date median is 0.87; the pooled fit is dominated by the dates with many quoted brackets).
Restricting to brackets Kalshi prices at 5¢ or more leaves b near 0.7, so it is not only the tick. But the economic
content is small: where the density says 0.6¢, Kalshi's ask is 2.0¢ and its bid 0.7¢, and 79% of those asks are at
1¢ or 2¢ — the longshot "premium" is one tick above fair plus a one-tick spread, and selling it means selling at the
bid, which is fair. The state tilt c is +0.023 per dollar at T-1d and −0.009 at T-4h: the two snapshots disagree on
its sign, so it is not a stable risk-premium reading. B1 holds on b; the structure exists; it is not an amount of
money.

**Friction is the finding.** The writeup's working figure of ~5¢ per contract round trip is not reachable with a
four-leg option replication on a $0.50 strike grid. Measured where legs were quoted, and estimated from the
synchronised chain's own half-spreads everywhere else, the stack is 7–30¢ per Kalshi dollar (median 12¢ at T-1d, 10¢
at T-4h), of which the CME spread term alone is 7–9¢: a 4–5¢/bbl half-spread on each leg is 8–10% of a $0.50
digital. Kalshi's own fee (0.6–1.8¢) and the CME fees at 500 contracts per structure (2.8¢) are secondary. Against
this the |gap| exceeds band + friction on 0 of 296 brackets, and 0 of 201 brackets with unquoted legs would clear
with the estimated friction either. No threshold choice inside the protocol changes that; the next pass inherits
whether any replication of a $1 bracket can be built for less than the gaps.

**The hedge is not priceable from this data, and the artifacts were real.** Only two brackets at T-1d and one at T-4h
had every leg quoted within five minutes of the snapshot; the TBBO carries a BBO only at trade instants, and legs 20–60
minutes old implied digitals 35¢ away from Act III on average. The first pass took those stale legs as executable and
produced one filtered trade with a −29¢ realised loss; it was removed by amendment 5 (leg freshness), and the date
itself fell to amendment 4: Kalshi's rules named no contract, the calendar fallback said CLM6, Kalshi settled on CLK6.
Three dates (01-16, 04-17, 05-15) carry that mismatch and are Gate 0b failures ex post. Both corrections are rules
about the data, written before any verdict, and both would have produced fedarb's failure mode if left in: a smooth,
confident, mis-centred disagreement. The residual-forward check is clean (median |E[F] − F₀| 3.4¢, correlation with
the per-date gap −0.08), and the sign of a bracket's gap at T-1d predicts its sign at T-4h on 49% of 271 brackets —
chance — so what little disagreement there is does not persist across four hours.

**The denominator.** 37 KXWTIW events since January; 3 with no same-day CME weekly on disk, 3 with the wrong contract,
2 with too few strikes, 1 (T-1d) / 2 (T-4h) split-half failures, 4 / 5 sampler failures, 24 / 22 cleared. Of the
brackets on dates reaching the comparison, 185 / 201 had no two-sided Kalshi quote at the snapshot (deep tails with
no bid), 93 / 133 had an executable price outside [2¢, 98¢], 201 / 103 lacked a fresh leg; 6 brackets sat in an
interior minimum of the density (none would have traded anyway); a LOO-flagged strike sat within $1 of an edge on 148
of 728 two-sided brackets. Depth could not be established from stored data at either 50 or 500 contracts and was not
assumed.

{KXWTI}

**What it means.** The strategy as specified — buy or sell a Kalshi bracket against a CL-option replication, held to
settlement — has no edge in this sample: not because the extraction is wrong, but because the prediction market
prices WTI weekly brackets within a cent of the options market, and the options replication costs ten times that.
The extractor passed the hardest test it has had, agreement with an independent venue on 535 brackets across 24 weeks,
and the question the next pass inherits is about the trade structure, not the density.
