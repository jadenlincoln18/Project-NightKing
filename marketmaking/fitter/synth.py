"""Synthetic temperature ladders with a known truth — PROTOCOL §8.2-§8.4.

Every number in this module is fixed by the pre-registration and none of it may
be retuned after a result is seen. The truth families, their parameter ranges,
the 6-bracket geometry and the noise scale are §8.2-§8.4 verbatim.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm, skewnorm

# --- geometry, measured (PROTOCOL §8.2) -------------------------------------
EDGES = np.array([-4.0, -2.0, 0.0, 2.0, 4.0])  # 5 interior edges, 2 degF apart
N_BRACKETS = len(EDGES) + 1                    # 6, as on 98.9% of real events

# --- quote noise, measured (PROTOCOL §8.4) ----------------------------------
SIGMA_Q = 0.0182        # sd(sum mid - 1)/sqrt(6) on 6,680 fully-tight ladder-minutes
OVERROUND = 0.0         # primary: quote unbiased. Sensitivity run uses 0.0356.
TICK = 0.01
MIN_CENTS, MAX_CENTS = 1.0, 99.0
SPREAD_STRATA = (0.0, 5.0, 15.0, 35.0, 65.0, 85.0, 95.0, 100.0)
TIGHT_MAX = 20.0        # spread below this is a price; at or above it is a 1/99 non-price

# PROTOCOL §9.9 adds a fourth family, "mix". The first three are §8.3 verbatim
# and the generator draws in family-block order, so the U/K/B blocks of a §9 run
# are bit-identical to what the §8.3 generator produces.
FAMILIES = ("unimodal", "skewed", "bimodal", "mix")


@dataclass
class Ladder:
    family: str
    truth_p: np.ndarray      # exact bracket probabilities of the known truth
    outcome: np.ndarray      # realised 0/1 settlement, exactly one 1
    bid: np.ndarray          # cents
    ask: np.ndarray          # cents
    draw: float              # the realised degF

    @property
    def quote_mid(self) -> np.ndarray:
        return (self.bid + self.ask) / 200.0

    @property
    def half_spread(self) -> np.ndarray:
        return (self.ask - self.bid) / 200.0


# --- truths ------------------------------------------------------------------

def _bracket_probs(cdf, edges=EDGES) -> np.ndarray:
    c = cdf(edges)
    return np.concatenate([[c[0]], np.diff(c), [1.0 - c[-1]]])


def draw_truth(family: str, rng: np.random.Generator):
    """Return (cdf, sampler) for one draw from the family's parameter prior."""
    if family == "unimodal":
        mu, sd = rng.uniform(-4, 4), rng.uniform(1.5, 4.0)
        return (lambda x: norm.cdf(x, mu, sd),
                lambda n: rng.normal(mu, sd, n),
                {"mu": mu, "sd": sd})
    if family == "skewed":
        xi, om = rng.uniform(-4, 4), rng.uniform(2.0, 4.5)
        al = float(rng.choice([-6.0, 6.0]))
        return (lambda x: skewnorm.cdf(x, al, xi, om),
                lambda n: skewnorm.rvs(al, xi, om, size=n, random_state=rng),
                {"xi": xi, "omega": om, "alpha": al})
    if family == "bimodal":
        delta, sd = rng.uniform(5, 9), rng.uniform(1.2, 2.2)
        centre, w = rng.uniform(-2, 2), rng.uniform(0.35, 0.65)
        m1, m2 = centre - delta / 2.0, centre + delta / 2.0

        def cdf(x):
            return w * norm.cdf(x, m1, sd) + (1 - w) * norm.cdf(x, m2, sd)

        def sampler(n):
            pick = rng.random(n) < w
            return np.where(pick, rng.normal(m1, sd, n), rng.normal(m2, sd, n))

        return cdf, sampler, {"m1": m1, "m2": m2, "sd": sd, "w": w, "delta": delta}
    if family == "mix":
        # PROTOCOL §9.9: the shouldered / fat-tailed / not-quite-bimodal middle
        # ground. Unequal component widths, separation down to zero.
        centre, delta = rng.uniform(-2, 2), rng.uniform(0.0, 5.0)
        sd1 = rng.uniform(1.2, 3.0)
        sd2 = sd1 * rng.uniform(1.5, 3.0)
        w = rng.uniform(0.3, 0.7)
        m1, m2 = centre - delta / 2.0, centre + delta / 2.0

        def cdf(x):
            return w * norm.cdf(x, m1, sd1) + (1 - w) * norm.cdf(x, m2, sd2)

        def sampler(n):
            pick = rng.random(n) < w
            return np.where(pick, rng.normal(m1, sd1, n), rng.normal(m2, sd2, n))

        return cdf, sampler, {"m1": m1, "m2": m2, "sd1": sd1, "sd2": sd2,
                              "w": w, "delta": delta}
    raise ValueError("unknown family %r" % family)


# --- quote noise -------------------------------------------------------------

class SpreadPool:
    """The measured tight-spread empirical distribution, resampled by mid level.

    Built from the real two-sided bracket-minutes with spread < 20c. The whole
    distribution is resampled, not its median, so the right tail of the spread
    survives into the synthetic quotes.
    """

    def __init__(self, df):
        self.pools = {}
        tight = df[df["spread"] < TIGHT_MAX]
        for i in range(len(SPREAD_STRATA) - 1):
            lo, hi = SPREAD_STRATA[i], SPREAD_STRATA[i + 1]
            sel = tight[(tight["mid"] > lo) & (tight["mid"] <= hi)] if i else \
                tight[tight["mid"] <= hi]
            v = sel["spread"].to_numpy(float)
            self.pools[i] = v if len(v) else tight["spread"].to_numpy(float)
        self.n_tight = int(len(tight))
        self.frac_tight = float(len(tight) / max(len(df), 1))

    def draw(self, mid_cents: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        idx = np.clip(np.searchsorted(np.asarray(SPREAD_STRATA[1:-1]), mid_cents,
                                      side="left"), 0, len(self.pools) - 1)
        return np.array([float(rng.choice(self.pools[int(i)])) for i in idx])


def quote_from_truth(p: np.ndarray, pool: SpreadPool, rng: np.random.Generator,
                     sigma_q: float = SIGMA_Q, overround: float = OVERROUND):
    """Noisy executable quotes around a truth. PROTOCOL §8.4.

    `m_i = p_i + e_i`, `e_i ~ N(0, sigma_q)`, then a spread resampled from the
    measured distribution for `m_i`'s level, placed symmetrically and rounded to
    the 1c tick. The scored quote is the resulting executable midpoint.
    """
    m = p * (1.0 + overround) + rng.normal(0.0, sigma_q, len(p))
    m_c = np.clip(m * 100.0, MIN_CENTS, MAX_CENTS)
    w = pool.draw(m_c, rng)
    bid = np.clip(np.round(m_c - w / 2.0), MIN_CENTS, MAX_CENTS - 1)
    ask = np.clip(bid + np.round(w), bid + 1, MAX_CENTS)
    return bid, ask


def make_ladder(family: str, pool: SpreadPool, rng: np.random.Generator,
                sigma_q: float = SIGMA_Q, overround: float = OVERROUND) -> Ladder:
    cdf, sampler, _par = draw_truth(family, rng)
    p = _bracket_probs(cdf)
    p = np.clip(p, 0.0, 1.0)
    p = p / p.sum()
    s = float(np.atleast_1d(sampler(1))[0])
    k = int(np.searchsorted(EDGES, s, side="right"))
    outcome = np.zeros(N_BRACKETS)
    outcome[k] = 1.0
    bid, ask = quote_from_truth(p, pool, rng, sigma_q=sigma_q, overround=overround)
    return Ladder(family=family, truth_p=p, outcome=outcome, bid=bid, ask=ask, draw=s)


def generate(n_per_family: int, pool: SpreadPool, rng: np.random.Generator,
             families=FAMILIES, **kw) -> list:
    return [make_ladder(f, pool, rng, **kw) for f in families for _ in range(n_per_family)]
