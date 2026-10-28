"""Kalshi trading fees, in cents per contract.

Published formula (fee schedule, verified 2026-10-05 against the series endpoint,
which reports fee_type='quadratic', fee_multiplier=1 for every ladder series used
here): fee = ceil(coef * C * P * (1 - P)) dollars per order, taker coef 0.07.
Maker orders pay a reduced coefficient of 0.0175 on markets where maker fees
apply (secondary sources; the schedule itself was rate-limited at the time of
writing - see FINDINGS_LADDER_DYNAMICS.md section on fees). Both are
parameters; nothing below hard-codes a verdict on the maker side.

Rounding is per ORDER, up to the next cent. Per contract that matters only for
tiny orders: at 1 contract and P=0.5 the fee is 2c, at 100 contracts 1.75c.
`fee_cents` returns the unrounded per-contract figure by default and the
rounded-per-order figure when `contracts` is given.
"""
import math

TAKER = 0.07
MAKER = 0.0175


def fee_cents(price_cents, coef=TAKER, contracts=None):
    """Fee in cents per contract at an executable price of `price_cents`."""
    p = min(max(float(price_cents) / 100.0, 0.0), 1.0)
    per = coef * p * (1.0 - p) * 100.0
    if contracts is None or contracts <= 0:
        return per
    total = math.ceil(round(coef * contracts * p * (1.0 - p) * 100.0, 9))  # cents, per order (round: fp noise must not add a cent)
    return total / float(contracts)


def two_leg_taker_fee(price_a, price_b):
    """Both legs crossed: fee on each at its own executable price."""
    return fee_cents(price_a) + fee_cents(price_b)
