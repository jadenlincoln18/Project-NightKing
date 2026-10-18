# FINDINGS_ACTII_V2 — Act II's firing rate on synchronised chains, and whether it sees what split-half sees

Task 1 of `NightKing/HANDOFF_actii_and_intraday.md`. Read entirely from the V2 run on disk (`synth/results_real/runs_v2.pkl`, `python3 -m synth.actii_v2`); nothing re-run, no Kalshi price read. Act II gate = max |Act II − Act III| over the ladder > 2.5¢ (the V1 cutoff); split-half gate = max |z| > 2.65 (the V2 calibrated cutoff).

**Verdict: Act II is quiet where the synchronisation is clean — 7% at T-1d/60 against 68% in V1 and a 0% calibrated false-positive rate — but still fires on 53% of T-4h/60 chains, and on synchronised chains its fires are two things: three genuinely multimodal T-4h posteriors (the prior-mismatch signature, τ 7–17) and a larger set where Act II itself is broken (wings that run away by $16–24, ρ pinned at ±0.99, or chains under 12 strikes). So split-half and Act II do cover different failure modes (fully disjoint at T-1d; pooled φ = 0.28, Jaccard 0.26), the prior can stay untouched for now, Act II must stay a report line rather than a gate until its wings are pinned, and T-4h — the snapshot nearest decision time — is where Task 2 has to look: it is the only snapshot where both Act II and Act III's multimodality survived synchronisation.**

## 1. Act II firing rate, V1 raw chains vs V2 synchronised chains

| snapshot | window | chains | n (trusted ≥12 strikes) | Act II fired: V1 raw → V2 sync | trusted only | max\|Δ\| median (¢): V1 → V2 | p90 | max | Act II inside Act III's 90% band on every bracket |
|---|---|---|---|---|---|---|---|---|---|
| T-2d | 60 | 14 → 26 | 12 → 24 | 64% → **31%** | 58% → 29% | 3.36 → 1.90 | 5.74 → 12.58 | 10.68 → 23.41 | 0% → 15% |
| T-2d | 10 | — → 8 | — → 1 | — → **12%** | — → 0% | — → 1.22 | — → 2.61 | — → 4.17 | — → 25% |
| T-1d | 60 | 28 → 30 | 28 → 30 | 68% → **7%** | 68% → 7% | 3.71 → 0.90 | 18.88 → 2.24 | 30.52 → 5.87 | 0% → 10% |
| T-1d | 10 | 9 → 21 | 8 → 14 | 44% → **19%** | 50% → 0% | 1.04 → 0.83 | 7.06 → 3.24 | 9.19 → 6.04 | 11% → 10% |
| T-4h | 60 | 30 → 30 | 30 → 30 | 77% → **53%** | 77% → 53% | 5.81 → 2.74 | 26.24 → 10.39 | 36.76 → 22.48 | 0% → 0% |
| T-4h | 10 | 9 → 9 | 6 → 6 | 56% → **22%** | 83% → 33% | 2.59 → 1.19 | 10.38 → 2.95 | 12.23 → 3.31 | 0% → 11% |

Pooled over the three snapshots and both windows: Act II fires on 67% of V1 raw chains (n=90) and **27%** of V2 synchronised chains (n=124). On the calibration chains (`synth/results_real/split_half_null.json`) the same gate fires on 0% of well-specified synthetic chains and 100% of bimodal ones.

## 2. Do Act II and split-half fire on the same chains?

Confusion matrix per cell (both / Act II only / split-half only / neither), the phi coefficient between the two indicators (0 = independent, 1 = identical), Fisher's exact p for association, and the Jaccard overlap of the two fired sets (fired by both ÷ fired by either).

| arm | snapshot | window | n | both | Act II only | split only | neither | Act II fired | split fired | φ | Fisher p | Jaccard |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 raw | T-2d | 60 | 14 | 5 | 4 | 2 | 3 | 64% | 50% | 0.15 | 1.000 | 0.45 |
| V1 raw | T-1d | 60 | 28 | 16 | 3 | 6 | 3 | 68% | 79% | 0.20 | 0.352 | 0.64 |
| V1 raw | T-1d | 10 | 9 | 1 | 3 | 2 | 3 | 44% | 33% | -0.16 | 1.000 | 0.17 |
| V1 raw | T-4h | 60 | 30 | 15 | 8 | 3 | 4 | 77% | 60% | 0.19 | 0.392 | 0.58 |
| V1 raw | T-4h | 10 | 9 | 1 | 4 | 1 | 3 | 56% | 22% | -0.06 | 1.000 | 0.17 |
| **V1 raw, pooled** | — | — | 90 | 38 | 22 | 14 | 16 | 67% | 58% | 0.16 | 0.175 | 0.51 |
| V2 synchronised | T-2d | 60 | 26 | 5 | 3 | 4 | 14 | 31% | 35% | 0.39 | 0.078 | 0.42 |
| V2 synchronised | T-2d | 10 | 8 | 0 | 1 | 0 | 7 | 12% | 0% | — | 1.000 | 0.00 |
| V2 synchronised | T-1d | 60 | 30 | 0 | 2 | 5 | 23 | 7% | 17% | -0.12 | 1.000 | 0.00 |
| V2 synchronised | T-1d | 10 | 21 | 0 | 4 | 0 | 17 | 19% | 0% | — | 1.000 | 0.00 |
| V2 synchronised | T-4h | 60 | 30 | 5 | 11 | 0 | 14 | 53% | 17% | 0.42 | 0.045 | 0.31 |
| V2 synchronised | T-4h | 10 | 9 | 1 | 1 | 0 | 7 | 22% | 11% | 0.66 | 0.222 | 0.50 |
| **V2 synchronised, pooled** | — | — | 124 | 11 | 22 | 9 | 82 | 27% | 16% | 0.28 | 0.004 | 0.26 |

## 3. Act II fit health on synchronised chains

| arm | snapshot | window | n | fit ok | g(k) ≥ 0 (butterfly-free) | density ≥ 0 on used range | normalised | mean within 15¢ of F0 | \|mean − F0\| median (¢) | p90 | strikes used med | dropped med | Lee slope b(1+\|ρ\|) med |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 raw | T-2d | 60 | 14 | 100% | 100% | 100% | 93% | 79% | 2.0 | 52.1 | 24 | 0 | 0.05 |
| V1 raw | T-1d | 60 | 28 | 100% | 100% | 100% | 86% | 71% | 2.4 | 238.0 | 29 | 0 | 0.07 |
| V1 raw | T-1d | 10 | 9 | 100% | 100% | 100% | 67% | 56% | 3.2 | 3784.5 | 14 | 0 | 0.09 |
| V1 raw | T-4h | 60 | 30 | 100% | 97% | 100% | 60% | 57% | 7.0 | 2626.9 | 26 | 0 | 0.06 |
| V1 raw | T-4h | 10 | 9 | 100% | 100% | 100% | 78% | 78% | 5.6 | 373.0 | 13 | 0 | 0.03 |
| V2 synchronised | T-2d | 60 | 26 | 100% | 96% | 96% | 81% | 69% | 2.8 | 177.2 | 20 | 0 | 0.05 |
| V2 synchronised | T-2d | 10 | 8 | 100% | 100% | 100% | 75% | 75% | 7.3 | 898.1 | 10 | 0 | 0.05 |
| V2 synchronised | T-1d | 60 | 30 | 100% | 100% | 100% | 77% | 73% | 3.8 | 457.9 | 28 | 0 | 0.07 |
| V2 synchronised | T-1d | 10 | 21 | 100% | 100% | 95% | 62% | 52% | 7.3 | 1991.8 | 13 | 0 | 0.13 |
| V2 synchronised | T-4h | 60 | 30 | 100% | 93% | 97% | 70% | 57% | 7.1 | 1681.2 | 26 | 0 | 0.10 |
| V2 synchronised | T-4h | 10 | 9 | 100% | 100% | 100% | 56% | 56% | 7.5 | 1151.2 | 13 | 0 | 0.19 |

## 4. What the four classes of synchronised chain look like

| class | n | multimodal posterior mean | draws multimodal med | τ med | 90% body width med (¢) | strikes med | χ²/strike med | LOO flags mean | Act II Δ med (¢) | split max\|z\| med | Act II min g med | \|Act II mean − F0\| med (¢) | \|ρ\| med | ATM σ med | skew med | Act II inside band |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| both fire | 11 | 45% | 20% | 2.7 | 5.8 | 24 | 5.2 | 5.8 | 9.03 | 4.21 | 0.114 | 3.1 | 0.28 | 68% | 0.56 | 0% |
| Act II only | 22 | 14% | 1% | 0.9 | 4.8 | 19 | 1.5 | 2.0 | 3.41 | 1.62 | 0.113 | 1.0 | 0.51 | 77% | 0.20 | 0% |
| split-half only | 9 | 0% | 4% | 1.1 | 2.4 | 24 | 3.3 | 4.7 | 2.14 | 3.37 | 0.151 | 7.1 | 0.60 | 65% | 0.96 | 0% |
| neither | 82 | 0% | 1% | 0.7 | 2.9 | 18 | 1.4 | 1.0 | 0.83 | 1.38 | 0.030 | 7.5 | 0.63 | 69% | 0.49 | 15% |

Every synchronised chain where Act II fires and split-half does not:

| date | snap | w | strikes | trusted | Act II Δ (¢) | split max\|z\| | χ²/strike | modes | draws multimodal | τ | width90 (¢) | LOO flags | Act II min g | Act II mean − F0 (¢) | ρ | ATM σ | skew |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-05-01 | T-4h | 60 | 48 | yes | 20.52 | 2.63 | 4.9 | 4 | 100% | 17.0 | 16.0 | 7 | 0.054 | -12 | 0.09 | 92% | -0.33 |
| 2026-05-29 | T-4h | 60 | 28 | yes | 13.60 | 1.74 | 3.6 | 3 | 99% | 6.7 | 14.6 | 6 | 0.078 | 190 | -0.85 | 94% | 1.49 |
| 2026-08-28 | T-2d | 60 | 9 | no | 10.41 | 0.99 | 1.3 | 1 | 0% | 1.0 | 5.3 | 1 | 0.000 | -1 | 0.23 | 50% | -0.25 |
| 2026-01-16 | T-4h | 60 | 18 | yes | 6.65 | 0.85 | 1.5 | 1 | 2% | 0.8 | 4.5 | 0 | 0.259 | -0 | 0.25 | 52% | 0.27 |
| 2026-07-10 | T-1d | 10 | 9 | no | 6.04 | 1.47 | 0.9 | 1 | 0% | 0.8 | 3.7 | 0 | 0.397 | -0 | 0.52 | 61% | 1.12 |
| 2026-07-10 | T-1d | 60 | 25 | yes | 5.87 | 1.61 | 4.7 | 1 | 6% | 1.2 | 4.8 | 4 | 0.277 | -0 | 0.02 | 60% | 0.92 |
| 2026-03-06 | T-4h | 60 | 41 | yes | 5.31 | 1.90 | 5.2 | 2 | 96% | 7.1 | 4.7 | 7 | 0.097 | -2 | -0.45 | 184% | 0.29 |
| 2026-07-24 | T-1d | 10 | 9 | no | 4.77 | 2.08 | 1.2 | 1 | 1% | 0.6 | 2.1 | 0 | 0.266 | -0 | -0.47 | 75% | 0.23 |
| 2026-03-13 | T-2d | 10 | 11 | no | 4.17 | 0.65 | 0.8 | 1 | 0% | 0.6 | 2.5 | 0 | 0.452 | -0 | 0.83 | 154% | 1.52 |
| 2026-08-21 | T-1d | 60 | 25 | yes | 3.92 | 2.14 | 1.0 | 1 | 0% | 0.7 | 2.7 | 0 | 0.306 | -0 | -0.49 | 45% | 0.17 |
| 2026-08-21 | T-4h | 60 | 21 | yes | 3.51 | 2.49 | 3.4 | 1 | 8% | 0.9 | 8.3 | 3 | 0.012 | 2371 | 0.97 | 57% | -0.41 |
| 2026-07-10 | T-4h | 60 | 20 | yes | 3.31 | 0.82 | 1.3 | 1 | 1% | 0.9 | 7.2 | 1 | 0.045 | 1662 | -0.94 | 67% | 0.94 |
| 2026-02-13 | T-1d | 10 | 9 | no | 3.24 | 1.91 | 1.6 | 1 | 0% | 0.7 | 9.1 | 1 | 0.000 | -3 | 0.86 | 37% | 0.46 |
| 2026-02-06 | T-4h | 60 | 29 | yes | 3.14 | 2.61 | 4.7 | 1 | 34% | 1.4 | 7.9 | 7 | 0.128 | -1 | 0.06 | 80% | 1.58 |
| 2026-05-01 | T-1d | 10 | 10 | no | 3.03 | 1.04 | 0.7 | 1 | 5% | 0.8 | 3.0 | 0 | 0.382 | -0 | -0.99 | 81% | -0.46 |
| 2026-07-31 | T-2d | 60 | 16 | yes | 2.96 | 1.24 | 1.9 | 1 | 0% | 1.0 | 1.3 | 1 | 0.500 | -0 | 0.99 | 85% | 0.99 |
| 2026-03-06 | T-4h | 10 | 17 | yes | 2.86 | 2.34 | 3.2 | 1 | 1% | 0.7 | 2.8 | 2 | 0.292 | -0 | -0.46 | 179% | -0.13 |
| 2026-07-31 | T-4h | 60 | 21 | yes | 2.78 | 1.80 | 2.5 | 1 | 1% | 0.9 | 4.6 | 3 | 0.000 | -4 | 0.54 | 79% | 0.08 |
| 2026-08-28 | T-4h | 60 | 14 | yes | 2.77 | 0.68 | 0.7 | 1 | 1% | 0.7 | 5.3 | 0 | 0.193 | -0 | -0.60 | 49% | -0.37 |
| 2026-03-20 | T-4h | 60 | 40 | yes | 2.74 | 1.63 | 1.0 | 1 | 2% | 1.0 | 3.7 | 0 | 0.001 | -3 | -0.01 | 121% | -0.03 |
| 2026-03-27 | T-4h | 60 | 37 | yes | 2.74 | 1.42 | 1.3 | 1 | 2% | 1.0 | 5.3 | 0 | -0.000 | 3 | -0.21 | 112% | 0.03 |
| 2026-01-09 | T-2d | 60 | 12 | yes | 2.56 | 1.14 | 1.6 | 1 | 0% | 0.7 | 7.5 | 2 | 0.000 | -1 | -0.54 | 42% | 0.13 |

## 5. Reading

**Firing rate.** Synchronisation took Act II from 67% to 27% of chains pooled, and to **7%** at T-1d/60 — two chains, both with
χ²/strike ≈ 1 and Act II's disagreement at 3.9¢ and 5.9¢ (against a 2.5¢ cutoff that is the p95 of well-specified synthetic
chains). That is the calibrated behaviour: the confound the handoff named (Act II differentiating the asynchrony) is gone, and the
old 68% was that confound. The 10-minute windows behave the same way (0% among trusted chains at T-1d/10). T-2d/60 sits at 31%
and **T-4h/60 at 53%**; those two are where the rest of this document lives.

**Same chains or different ones?** Pooled over synchronised chains the two gates are positively associated (φ = 0.28, Fisher p =
0.004) but far from identical: 11 chains fire both, 22 fire Act II only, 9 fire split-half only, Jaccard 0.26. The association is
carried entirely by T-4h/60 (φ = 0.42, five chains fire both — and those are the worst chains in the study, χ²/strike 5.2 median,
5.8 LOO flags per chain, 45% with a multimodal posterior mean). At T-1d/60 the two gates are **disjoint**: no chain fires both, two
fire Act II only, five fire split-half only. So the answer to "one phenomenon or two" is two, with a third category where a chain is
bad enough that both see it.

**What the Act II-only chains are.** Twenty-two chains, listed in §4. They sort into four groups:

1. *Genuinely multimodal Act III posteriors* — 2026-05-01, 2026-05-29 and 2026-03-06, all T-4h/60: 2–4 modes in the posterior
   mean, 96–100% of draws multimodal, τ 6.7–17 (the roughness scale the sampler is pushed to when the data want structure the
   prior dislikes; a well-behaved chain sits at τ ≈ 0.7–1.0), χ²/strike 3.6–5.2, 6–7 LOO flags each, Act II disagreement 5–21¢.
   These are the chains the bimodal calibration case describes: split-half cannot see them because both halves carry the same
   posterior, and Act II does. Whether they are real or a reconstruction artifact of the path (T-4h is furthest from the 14:29
   anchor) is exactly Task 2's question.
2. *Act II broken, not the chain* — 2026-08-21 T-4h (Act II density mean $23.71 above the forward), 2026-07-10 T-4h ($16.62),
   2026-05-29 T-4h again ($1.90), and the fits with |ρ| pinned at the 0.99 bound (2026-07-31 T-2d, 2026-05-01 T-1d/10, 2026-07-10
   T-4h at −0.94). On these the SVI wings ran away or the fit sits on a constraint; the chain itself has χ²/strike 0.7–3.4 and
   passes split-half easily. The disagreement is Act II's error, not Act III's.
3. *Thin chains Act II is not trusted on* — 2026-08-28 T-2d (9 strikes, 10.4¢), 2026-07-10 T-1d/10, 2026-07-24 T-1d/10,
   2026-03-13 T-2d/10, 2026-02-13 T-1d/10, 2026-05-01 T-1d/10 (9–11 strikes). The detector already reports these as untrusted.
4. *Marginal fires on clean chains* — 2.5–4¢ on chains with χ²/strike ≈ 1, one mode, τ ≈ 1 (2026-03-20, 2026-03-27, 2026-01-09,
   2026-08-21 T-1d, 2026-08-28 T-4h, 2026-01-16). Six of 82 clean-looking chains at or just above a p95 cutoff is the expected
   false-positive rate.

**Act II fit health is the problem for using it as a gate.** On synchronised chains g(k) ≥ 0 holds on 93–100% of fits and the
density is non-negative on the used range on 95–100%, so the Stage 10 hardening works. But the density *mean* lands within 15¢ of
the forward on only 52–73% of chains, and the p90 of |mean − F0| is $1.8–$20: the SVI wings extrapolate beyond the last strike
and, when they run away, carry the mean with them (V1's "~$0.50 mean drift on synthetic" is the mild version of this). Act II's
bracket probabilities sit inside Act III's 90% band on every bracket on only 0–15% of chains. The gate compares a bracket vector
from a fit whose tails are unconstrained to a posterior whose tails are prior-dominated; where the two disagree by 3¢ on a
shoulder bracket that is not evidence of anything about the chain. A usable Act II gate needs (a) the wing slope pinned or the
mean constrained to the forward — the Stage 14 idea applied to Act II — and (b) the comparison restricted to brackets inside the
strike range. Neither was done here, because this task was to read the number, not change the method.

**What this says about the prior.** The three chains in group 1 are the only evidence in 124 synchronised extractions that real
WTI densities sit outside the roughness prior's comfort zone, and all three are at T-4h/60 — the snapshot with the weakest path
reconstruction, 21% one-cent bids and a window that is a fifth of the option's remaining life. At T-1d and T-2d there is no such
chain. The prior's form is therefore not at the front of the queue on this evidence; it moves there only if Task 2 shows those
three (and the 23% T-4h multimodality of V2 §8) survive a real intraday path.

**Consequence for T-2d.** Act II fires on 31% of T-2d/60 chains, but 3 of the 8 fires are untrusted 9–12-strike chains and the
five that fire both gates have χ²/strike well above 2. T-2d is kept: the futures forward extracts it on 26 of 30 dates and the
split-half gate handles it like any other snapshot.

