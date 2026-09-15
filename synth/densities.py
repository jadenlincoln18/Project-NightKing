"""Planted risk-neutral densities with exact pricing.

Every family is defined by its log-density in x = log(s/F0), evaluated on a fine
grid (20,001 points, +-14 vol-scales), normalised, and then re-centred in x until
the mean is exactly F0 (martingale). Prices are the discounted payoff integral
against that grid, so "exact" here means accurate to ~1e-7 dollars.

Families
  lognormal      Black-76 control; Act II is exactly right here
  crude_skew     skewed, fat upper tail: 3-component mixture in log space
  bimodal        two separated humps (binary supply event); trough between them
  bimodal_close  humps 1.6 vol-scales apart - likely indistinguishable from unimodal
  heavy_both     Student-t (nu=3) in log space; both tails fat
  sharp_peak     Laplace in log space; a kink at the mode the smooth prior dislikes
  spike          80% lognormal + 20% very narrow spike; truth outside the prior
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional

import numpy as np

FAMILIES = ("lognormal", "crude_skew", "bimodal", "bimodal_close", "heavy_both", "sharp_peak", "spike")
REQUIRED = ("crude_skew", "bimodal")


def _log_mix(x, comps):
    """log of a mixture of normals in x. comps: [(weight, mu, sd), ...]"""
    acc = np.full_like(x, -np.inf)
    for w, mu, sd in comps:
        lp = np.log(w) - 0.5 * ((x - mu) / sd) ** 2 - np.log(sd)
        acc = np.logaddexp(acc, lp)
    return acc


def log_density_x(family: str, x: np.ndarray, v: float) -> np.ndarray:
    """Unnormalised log-density in x = log(s/F0); v = sigma*sqrt(T) is the vol scale."""
    if family == "lognormal":
        return -0.5 * ((x + 0.5 * v * v) / v) ** 2
    if family == "crude_skew":
        return _log_mix(x, [(0.75, 0.0, 0.85 * v), (0.20, 0.8 * v, 1.5 * v), (0.05, 2.5 * v, 2.5 * v)])
    if family == "bimodal":
        return _log_mix(x, [(0.55, -1.2 * v, 0.5 * v), (0.45, 1.4 * v, 0.6 * v)])
    if family == "bimodal_close":
        return _log_mix(x, [(0.5, -0.8 * v, 0.55 * v), (0.5, 0.8 * v, 0.55 * v)])
    if family == "heavy_both":
        nu = 3.0
        return -0.5 * (nu + 1.0) * np.log1p((x / (0.8 * v)) ** 2 / nu)
    if family == "sharp_peak":
        return -np.abs(x) / (0.6 * v)
    if family == "spike":
        return _log_mix(x, [(0.8, 0.0, v), (0.2, 1.5 * v, 0.05 * v)])
    raise ValueError("unknown family %r" % family)


class Planted:
    """A planted density on a fine grid with exact pricing and bracket integrals."""

    def __init__(self, family: str, F0: float, sigma: float, T: float, n_grid: int = 20001, span_sd: float = 14.0,
                 r: float = 0.04):
        self.family = family
        self.F0 = float(F0)
        self.sigma = float(sigma)
        self.T = float(T)
        self.r = float(r)
        self.D = float(np.exp(-r * T))
        v = sigma * np.sqrt(T)
        self.v = v
        x = np.linspace(-span_sd * v, span_sd * v, n_grid)
        lp = log_density_x(family, x, v)
        # re-centre in x until E[s] = F0 exactly (martingale property)
        shift = 0.0
        for _ in range(60):
            s = F0 * np.exp(x + shift)
            px = np.exp(lp - lp.max())
            px /= np.trapz(px, s)
            mean = np.trapz(s * px, s)
            shift -= np.log(mean / F0)
            if abs(mean / F0 - 1.0) < 1e-13:
                break
        self.s = F0 * np.exp(x + shift)
        px = np.exp(lp - lp.max())
        self.f = px / np.trapz(px, self.s)
        # trapezoid weights -> discrete masses
        h = np.diff(self.s)
        w = np.zeros_like(self.s)
        w[:-1] += 0.5 * h
        w[1:] += 0.5 * h
        self.p = self.f * w
        self.p /= self.p.sum()
        self.cum = np.concatenate([[0.0], np.cumsum(self.p)])
        self.s_edges = np.concatenate([[self.s[0]], 0.5 * (self.s[1:] + self.s[:-1]), [self.s[-1]]])
        self.mean = float(np.sum(self.p * self.s))
        self.std = float(np.sqrt(np.sum(self.p * (self.s - self.mean) ** 2)))

    def pdf(self, x) -> np.ndarray:
        return np.interp(np.asarray(x, float), self.s, self.f, left=0.0, right=0.0)

    def cdf(self, x) -> np.ndarray:
        return np.interp(np.asarray(x, float), self.s_edges, self.cum, left=0.0, right=1.0)

    def price(self, K, right="C") -> np.ndarray:
        K = np.atleast_1d(np.asarray(K, float))
        pay = np.maximum(self.s[None, :] - K[:, None], 0.0)
        call = self.D * pay @ self.p
        if isinstance(right, str):
            return call if right == "C" else call - self.D * (self.F0 - K)
        return np.where(np.asarray(right) == "C", call, call - self.D * (self.F0 - K))

    def bracket_probs(self, edges: Iterable[float]) -> np.ndarray:
        """P(a <= F_T < b) for consecutive edges; the first and last brackets are open
        (below the first edge, above the last)."""
        e = np.asarray(list(edges), float)
        c = self.cdf(e)
        return np.concatenate([[c[0]], np.diff(c), [1.0 - c[-1]]])

    def describe(self) -> Dict[str, float]:
        return {"family": self.family, "F0": self.F0, "sigma": self.sigma, "T": self.T, "mean": self.mean,
                "std": self.std, "v": self.v}


def kalshi_edges(F0: float, half_width: int = 12) -> np.ndarray:
    """$1-wide Kalshi-like ladder around F0: 'X or above' thresholds at whole dollars,
    edges at X - 0.005 (Kalshi's T79.99 style)."""
    base = int(np.floor(F0))
    return np.array([base - half_width + j - 0.005 for j in range(2 * half_width + 1)], float)
