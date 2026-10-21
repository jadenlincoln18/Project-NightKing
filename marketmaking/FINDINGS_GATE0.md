# FINDINGS — Gate 0 (PROTOCOL §1B "Gate 0", specified in §8)

**Date:** 2026-10-20
**Branch:** `claude/gracious-edison-s2s7t5`
**Pre-registration:** `PROTOCOL.md` §8, committed **`3dcd015`** and pushed
**before a single synthetic ladder existed**. §1B is not modified by this run.

> **The question.** `BRIEF.md` §2 claims the fit beats a bracket's own quote by
> pooling **~25 noisy observations of one distribution**. The §1A universe
> supplies **6**. Gate 0 hands the fitter a truth it already knows the answer to
> and asks whether, at six brackets, it still wins.

---

## 1. What was measured on the real ladders first

Gate 0's synthetic ladders are not invented shapes. Their geometry and their
quote noise are measured from the staged store, and nothing else about the real
data is read — **no settlement outcome enters anything that is scored here.**
§1A explicitly permits microstructure as a design input.

### 1.1 Geometry — all 48 staged temperature series, 15,523 classifiable events

| quantity | measured | source |
|---|---|---|
| Brackets per event | **5.989 mean**; exactly 6 on **15,355 / 15,523 = 98.9%** | `fit/geometry.py` |
| Interior edge spacing | **2.0 °F** on 61,771 of 61,927 gaps (**99.7%**) | " |
| Interior span | **8.0 °F** median | " |
| Ladder kind | `range` on 15,712 events; `cumul` on **zero** | " |

A real ladder is literally `≤29 | 30–31 | 32–33 | 34–35 | 36–37 | ≥38`: four
2 °F interior brackets and two open wings. Measured strike conventions on this
universe: `less` carries an **exclusive** cap, `greater` an **exclusive** floor,
`between` an inclusive `[floor, cap]`; settlement is on integer °F, so the
continuous bracket boundaries fall on the half degree. The synthetic ladders use
exactly this: edges at `{−4, −2, 0, +2, +4}` °F, six brackets, open wings.

### 1.2 Quote noise — two independent measurements that agree

**(a) From the ladder's own arithmetic.** A `range` ladder partitions the
outcome space, so coherent mids sum to 1. With `m_i = p_i + e_i` and independent
`e_i`, `sd(Σm − 1) = σ_q √n_br`. On **6,680 fully-tight ladder-minutes** across
12 series (every bracket two-sided, every spread < 20c):

```
sd(Σ mid − 1) = 0.0445     n_br = 6.0     =>   σ_q = 0.0182   (1.8 cents)
mean(Σ mid − 1) = +0.0356  — the overround, a systematic quantity, not noise
```

This measures the **idiosyncratic** component only; common-mode error cancels in
the sum. That is the right component: a common-mode error is one the fit absorbs
rather than corrects, so counting it would credit the fit with knowledge it does
not have.

**(b) From the spread.** On 45,338 two-sided executable bracket-minutes,
**26.3% are degenerate 1/99-type books** (spread ≥ 20c; 8.1% at ≥ 90c) — quoted
in the data, but not prices. On the remaining 73.7% the median spread by mid
level (cents) is:

| mid (c) | 0–5 | 5–15 | 15–35 | 35–65 | 65–85 | 85–95 | 95–100 |
|---|---|---|---|---|---|---|---|
| median spread | 2 | 5 | 5 | 4 | 6 | 9 | 1 |

Median half-spread **≈ 2c**, independently agreeing with σ_q = 1.8c. The two
numbers come from unrelated features of the data — one from cross-sectional
incoherence, one from the touch — and they land in the same place, so the noise
scale Gate 0 uses is not a guess.

### 1.3 The two conservative choices, both made before any result

1. **Degenerate books excluded from the noise model.** Including 1/99 books
   would hand the quote comparator a 26% subset of mid-50 non-prices and let the
   fit win on arithmetic rather than on knowledge.
2. **No overround in the primary.** Real mids sum to 1.0356; a fitted density
   normalises to 1 by construction and would cancel that bias for free. The
   primary run sets the overround to zero so the quote is **unbiased**. The
   measured +3.56% is run as a declared sensitivity.

Both choices make the gate **harder** to pass. That was the point of fixing them
in advance.

---

## 2. What was built

New code under `marketmaking/fit/`. **`wti_arb/synth/`, `ladder/` and `waves/`
are not modified, not patched and not imported for inference.** `ladder.store`
is read read-only for the geometry and spread measurements above.

| module | what it is |
|---|---|
| `fit/geometry.py` | the §1.1–§1.2 measurements |
| `fit/density.py` | the fitter: **linear °F grid**, **indicator payoff**, spline log-density, posterior band90 |
| `fit/nuts.py` | the sampler, **copied verbatim** from `act3.py` (Whitened, NUTS, split-Rhat, ESS) |
| `fit/synth.py` | truth families, realised settlement, measured quote noise |
| `fit/gate0.py` | the driver, the disagreement sets, the Brier scoring, the verdict |

### 2.1 The one structural change, and why it was unavoidable

The WTI extractor's payoff matrix is `G[i,k] = (s_k − K_i)⁺` on a grid
`s = F₀·exp(x)`, `x ∈ ±extent_sd·σ√T`. A daily temperature has **no forward
`F₀`**, **no implied volatility**, and a support that reaches 0 °F and below,
where `log(s/F₀)` does not exist. And a Kalshi bracket is **not a vanilla**: it
is a digital on an interval, already a probability.

```
WTI :  Chat_i = Σ_k D·(s_k − K_i)⁺ · p_k          s linear in log-moneyness
Gate 0: Chat_i = Σ_k 1{s_k ∈ bracket_i} · p_k      s linear in degrees Fahrenheit
```

Because `p` is normalised by construction, `G@p` **is** the model's predicted
bracket probability, and the columns of `G` sum to 1. Cells straddling an edge
are split in proportion to the overlap, so a boundary between grid points does
not quantise the likelihood.

Everything else is the extractor's, reproduced not retuned: cubic B-spline
log-density with **m = 24** coefficients, sum-zero gauge, second-difference
P-spline prior whose smoothing scale `τ` is integrated out by quadrature,
`N(0, 30²)` on the exponential tilt, Gaussian likelihood with **sd = the
half-spread**, dense Gauss-Newton metric at the MAP, NUTS in whitened
coordinates, and **band90 = the posterior 5th/95th percentile per bracket,
asymmetric as drawn**. No martingale constraint, because there is no forward to
constrain to.

**m = 24 was deliberately not reduced.** Twenty-four coefficients against six
prices is exactly the prior-dominated regime Gate 0 exists to measure. Tuning it
down to make the fit look better is the move the pre-registration forbids.

---
