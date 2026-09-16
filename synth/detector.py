"""Gate 4: the Act II / Act III disagreement detector.

Both routes are already computed; the gate is the largest absolute difference between
Act II's bracket probability and Act III's posterior-mean bracket probability over the
Kalshi ladder, in cents. The cutoff and its justification come from the synthetic
study (FINDINGS_SYNTHETIC.md §11): re-fitting the hardened Act II on every stored
synthetic run, the disagreement on well-specified chains with >= 12 strikes has p95 and
p99 given below, and on the mis-specified shapes (bimodal, spike, kink) it sits an order
of magnitude higher. Chains with fewer than 12 strikes give Act II too little to fit
and the detector is reported but not trusted there.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

CUTOFF_CENTS = 2.5      # see FINDINGS_SYNTHETIC.md §11 for the ROC table behind this number
MIN_STRIKES_TRUSTED = 12


def disagreement_cents(act2_bracket: np.ndarray, act3_bracket_mean: np.ndarray) -> float:
    return float(100.0 * np.max(np.abs(np.asarray(act2_bracket) - np.asarray(act3_bracket_mean))))


def gate(act2_bracket: Optional[np.ndarray], act3_bracket_mean: np.ndarray, n_strikes: int,
         cutoff: float = CUTOFF_CENTS) -> Dict[str, object]:
    """Returns {'fired': bool, 'trusted': bool, 'cents': float|None, 'reason': str}."""
    if act2_bracket is None:
        return {"fired": True, "trusted": True, "cents": None, "reason": "Act II did not produce a usable fit"}
    d = disagreement_cents(act2_bracket, act3_bracket_mean)
    trusted = n_strikes >= MIN_STRIKES_TRUSTED
    fired = d > cutoff
    reason = ("Act II and Act III disagree by %.2fc on a bracket (cutoff %.1fc)" % (d, cutoff)) if fired else "agree"
    if not trusted:
        reason += "; %d strikes < %d, detector not trusted on thin chains" % (n_strikes, MIN_STRIKES_TRUSTED)
    return {"fired": bool(fired), "trusted": bool(trusted), "cents": d, "reason": reason}
