"""Posterior machinery for `fit/density.py` — copied from `wti_arb/synth/act3.py`.

**This is a copy, deliberately.** PROTOCOL §8.5 fixes the sampler as the one the
WTI extractor already uses, and the extractor itself may not be modified or
depended on. Importing it would couple Gate 0 to a module whose `Model` is an
options-chain object; copying the payoff-agnostic parts — the whitened
reparameterisation, NUTS, split-Rhat and ESS — keeps `wti_arb/synth/` untouched
while running the identical inference.

Copied verbatim from `act3.py` (lines 258-279, 282-446, 527-572) so that no
transcription error can make Gate 0's sampler differ from the validated one:

  * `Whitened`   — psi = centre + L xi, the dense-metric reparameterisation
  * `NUTS`       — Hoffman & Gelman (2014) Alg. 6, dual-averaging step size
  * `split_rhat`, `ess` — convergence diagnostics

The only edit is this docstring and the import block. `model` is duck-typed: it
needs `dim` and `logpost(q, with_grad)`, which `fit.density.LadderModel`
provides.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np


class Whitened:
    """psi = centre + L xi; exposes logpost(xi) for the sampler."""

    def __init__(self, model: Model, centre: np.ndarray, L: np.ndarray):
        self.model = model
        self.centre = centre
        self.L = L
        self.dim = model.dim

    def logpost(self, xi: np.ndarray, with_grad: bool = True):
        psi = self.centre + self.L @ xi
        if not with_grad:
            return self.model.logpost(psi, False)
        lp, g = self.model.logpost(psi)
        return lp, self.L.T @ g

    def psi(self, xi: np.ndarray) -> np.ndarray:
        return self.centre + xi @ self.L.T


# --------------------------------------------------------------------------
# NUTS


class NUTS:
    def __init__(self, model, rng: np.random.Generator, max_depth: int = 8, target_accept: float = 0.8,
                 final_frac: float = 0.25):
        self.m = model
        self.rng = rng
        self.max_depth = max_depth
        self.delta = target_accept
        self.final_frac = final_frac  # share of warmup after the last metric update (Stan: 10%; we need more)
        self.divergences = 0
        self.depths: List[int] = []

    def _leapfrog(self, q, p, grad, eps, inv_mass):
        p = p + 0.5 * eps * grad
        q = q + eps * inv_mass * p
        lp, grad = self.m.logpost(q)
        if not np.isfinite(lp):
            lp = -np.inf
            grad = np.zeros_like(grad)
        p = p + 0.5 * eps * grad
        return q, p, lp, grad

    def _find_eps(self, q, inv_mass):
        eps = 1.0
        lp, grad = self.m.logpost(q)
        p = self.rng.standard_normal(q.size) / np.sqrt(inv_mass)
        H0 = -lp + 0.5 * np.sum(inv_mass * p * p)
        q1, p1, lp1, _ = self._leapfrog(q, p, grad, eps, inv_mass)
        H1 = -lp1 + 0.5 * np.sum(inv_mass * p1 * p1)
        a = 1.0 if (np.isfinite(H1) and (H0 - H1) > np.log(0.5)) else -1.0
        for _ in range(60):
            eps *= 2.0 ** a
            q1, p1, lp1, _ = self._leapfrog(q, p, grad, eps, inv_mass)
            H1 = -lp1 + 0.5 * np.sum(inv_mass * p1 * p1)
            if not np.isfinite(H1):
                if a > 0:
                    eps /= 2.0
                    break
                continue
            if a * (H0 - H1) < a * np.log(0.5):
                break
        return float(np.clip(eps, 1e-8, 10.0))

    def _build(self, q, p, grad, logu, v, j, eps, H0, inv_mass):
        if j == 0:
            q1, p1, lp1, g1 = self._leapfrog(q, p, grad, v * eps, inv_mass)
            H1 = -lp1 + 0.5 * np.sum(inv_mass * p1 * p1)
            if not np.isfinite(H1):
                H1 = np.inf
            n1 = 1 if logu <= -H1 else 0
            s1 = 1 if logu < 1000.0 - H1 else 0
            if s1 == 0:
                self.divergences += 1
            alpha = float(min(1.0, np.exp(min(H0 - H1, 0.0)))) if np.isfinite(H1) else 0.0
            return q1, p1, g1, q1, p1, g1, q1, lp1, n1, s1, alpha, 1
        qm, pm, gm, qp, pp, gp, q1, lp1, n1, s1, a1, na1 = self._build(q, p, grad, logu, v, j - 1, eps, H0, inv_mass)
        if s1 == 1:
            if v == -1:
                qm, pm, gm, _, _, _, q2, lp2, n2, s2, a2, na2 = self._build(qm, pm, gm, logu, v, j - 1, eps, H0, inv_mass)
            else:
                _, _, _, qp, pp, gp, q2, lp2, n2, s2, a2, na2 = self._build(qp, pp, gp, logu, v, j - 1, eps, H0, inv_mass)
            if n1 + n2 > 0 and self.rng.uniform() < n2 / float(n1 + n2):
                q1, lp1 = q2, lp2
            a1 += a2
            na1 += na2
            dq = qp - qm
            s1 = s2 * (1 if (dq @ (inv_mass * pm)) >= 0 else 0) * (1 if (dq @ (inv_mass * pp)) >= 0 else 0)
            n1 += n2
        return qm, pm, gm, qp, pp, gp, q1, lp1, n1, s1, a1, na1

    def run(self, q0: np.ndarray, n_warmup: int, n_samples: int, inv_mass: Optional[np.ndarray] = None,
            adapt_mass: bool = True, keep_warmup: bool = False) -> Dict[str, object]:
        q = np.array(q0, float)
        d = q.size
        warm_draws = np.empty((n_warmup, d)) if keep_warmup else None
        inv_mass = np.ones(d) if inv_mass is None else np.array(inv_mass, float)
        eps = min(self._find_eps(q, inv_mass), 0.5)
        mu = np.log(10.0 * eps)
        self.eps_trace: List[float] = []
        Hbar, log_eps_bar, gamma, t0, kappa = 0.0, 0.0, 0.05, 10.0, 0.75
        lp, grad = self.m.logpost(q)
        draws = np.empty((n_samples, d))
        lps = np.empty(n_samples)
        win_end: List[int] = []
        if adapt_mass and n_warmup >= 100:
            a = int(0.15 * n_warmup)
            b = n_warmup - int(self.final_frac * n_warmup)
            size = 25
            cur = a
            while cur + size < b:
                cur += size
                win_end.append(cur)
                size *= 2
            win_end.append(b)
        win_buf: List[np.ndarray] = []
        self.depths = []
        accept_stats: List[float] = []
        da_it = 0  # dual-averaging iteration counter; restarts with every metric window
        for it in range(n_warmup + n_samples):
            p0 = self.rng.standard_normal(d) / np.sqrt(inv_mass)
            H0 = -lp + 0.5 * np.sum(inv_mass * p0 * p0)
            logu = -H0 + np.log(self.rng.uniform())
            qm = qp = q
            pm = pp = p0
            gm = gp = grad
            j, n, s = 0, 1, 1
            q_new, lp_new = q, lp
            alpha, n_alpha = 0.0, 1
            while s == 1 and j < self.max_depth:
                v = 1 if self.rng.uniform() < 0.5 else -1
                if v == -1:
                    qm, pm, gm, _, _, _, q1, lp1, n1, s1, alpha, n_alpha = self._build(qm, pm, gm, logu, v, j, eps, H0, inv_mass)
                else:
                    _, _, _, qp, pp, gp, q1, lp1, n1, s1, alpha, n_alpha = self._build(qp, pp, gp, logu, v, j, eps, H0, inv_mass)
                if s1 == 1 and self.rng.uniform() < min(1.0, n1 / float(n)):
                    q_new, lp_new = q1, lp1
                n += n1
                dq = qp - qm
                s = s1 * (1 if (dq @ (inv_mass * pm)) >= 0 else 0) * (1 if (dq @ (inv_mass * pp)) >= 0 else 0)
                j += 1
            self.depths.append(j)
            if q_new is not q:
                q, lp = q_new, lp_new
                _, grad = self.m.logpost(q)
            accept_stat = alpha / max(n_alpha, 1)
            if it < n_warmup:
                if warm_draws is not None:
                    warm_draws[it] = q
                da_it += 1
                m_it = da_it
                Hbar = (1 - 1.0 / (m_it + t0)) * Hbar + (self.delta - accept_stat) / (m_it + t0)
                log_eps = mu - np.sqrt(m_it) / gamma * Hbar
                eta = m_it ** (-kappa)
                log_eps_bar = eta * log_eps + (1 - eta) * log_eps_bar
                eps = float(np.exp(log_eps))
                self.eps_trace.append(eps)
                if win_end:
                    win_buf.append(q.copy())
                    if it + 1 == win_end[0]:
                        arr = np.array(win_buf)
                        nw = len(arr)
                        var = arr.var(axis=0, ddof=1) if nw > 5 else np.ones(d)
                        # regularise toward the whitened scale (1), not toward 1e-3
                        inv_mass = np.maximum((nw / (nw + 5.0)) * var + (5.0 / (nw + 5.0)) * 1.0, 1e-6)
                        win_buf = []
                        win_end.pop(0)
                        eps = min(self._find_eps(q, inv_mass), 0.5)
                        mu = np.log(10.0 * eps)
                        Hbar, log_eps_bar, da_it = 0.0, 0.0, 0
                if it + 1 == n_warmup:
                    eps = float(np.exp(log_eps_bar))
                    self.divergences = 0
            else:
                draws[it - n_warmup] = q
                lps[it - n_warmup] = lp
                accept_stats.append(accept_stat)
        return {"draws": draws, "logpost": lps, "eps": eps, "inv_mass": inv_mass, "divergences": self.divergences,
                "mean_depth": float(np.mean(self.depths[n_warmup:])) if n_samples else 0.0,
                "accept": float(np.mean(accept_stats)) if accept_stats else 0.0, "warm_draws": warm_draws,
                "last": q}


# --------------------------------------------------------------------------
# coordinate slice sampler (whitened coordinates)
# --------------------------------------------------------------------------



def split_rhat(chains: np.ndarray) -> np.ndarray:
    c, n, d = chains.shape
    half = n // 2
    parts = np.concatenate([chains[:, :half], chains[:, half:2 * half]], axis=0)
    n2 = half
    means = parts.mean(axis=1)
    vars_ = parts.var(axis=1, ddof=1)
    W = vars_.mean(axis=0)
    B = n2 * means.var(axis=0, ddof=1)
    var_hat = (n2 - 1) / n2 * W + B / n2
    return np.sqrt(var_hat / np.maximum(W, 1e-300))


def ess(chains: np.ndarray) -> np.ndarray:
    """Bulk ESS per dimension: pooled autocorrelation, Geyer initial positive sequence."""
    c, n, d = chains.shape
    out = np.empty(d)
    for k in range(d):
        x = chains[:, :, k]
        x = x - x.mean(axis=1, keepdims=True)
        var = x.var(axis=1, ddof=1).mean()
        if var <= 0:
            out[k] = c * n
            continue
        acf = np.zeros(n)
        for ch in range(c):
            f = np.fft.rfft(np.concatenate([x[ch], np.zeros(n)]))
            acf += np.fft.irfft(f * np.conj(f))[:n] / n
        acf /= (c * var)
        rho_sum, t, prev_pair = 0.0, 1, np.inf
        while t + 1 < n:
            pair = acf[t] + acf[t + 1]
            if pair < 0:
                break
            pair = min(pair, prev_pair)
            rho_sum += pair
            prev_pair = pair
            t += 2
        out[k] = c * n / max(1.0 + 2.0 * rho_sum, 1e-6)
    return out


# --------------------------------------------------------------------------
# drivers
# --------------------------------------------------------------------------

