"""Static configuration for the marketmaking stack.

Universe and constants come from PROTOCOL.md. Where a value here contradicts
PROTOCOL.md, PROTOCOL.md wins and this file is the bug.
"""
from __future__ import annotations

import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent          # marketmaking/
REPO = ROOT.parent                                             # Project-NightKing/
DATA = pathlib.Path(os.environ.get("MM_DATA", ROOT / "data"))
LOGS = pathlib.Path(os.environ.get("MM_LOGS", ROOT / "logs"))
REPORTS = ROOT / "reports"

# --- kill switch -------------------------------------------------------------
# A single file. Present => all quoting stops and everything is cancelled.
# Checkable by operator and agent, honoured within one cycle (PROTOCOL §7).
KILL_FILE = ROOT / "KILL"

# --- phase gate --------------------------------------------------------------
# The order manager is inert for the whole of phase 1. This is belt and braces
# alongside there being no authenticated code path at all.
PHASE = int(os.environ.get("MM_PHASE", "1"))
ORDERS_ENABLED = False          # never flipped by config; phase 3 is a code change

# --- fee ---------------------------------------------------------------------
# PROTOCOL §1: maker fee is structurally zero on the quoting universe.
MAKER_FEE_CENTS = 0.0

_FEE_MAP = json.loads((ROOT / "fee_map_ladder.json").read_text())
ALL_SERIES = sorted(x["series"] for x in _FEE_MAP)
MAKER_FEE_SERIES = sorted(
    x["series"] for x in _FEE_MAP if x["fee_type"] == "quadratic_with_maker_fees"
)

# PROTOCOL §1A (2026-10-18): universe fixed from the coverage map, before any
# shadow output existed. Three labelled groups, collected together so the
# comparison is same-window and same-collector.
#
#   PRIMARY    51 uncovered daily city temperature ladders. The provider left
#              (on the June LPP list, absent from lpp_2026-10-18.json) and the
#              volume stayed. All 51 are fee_type "quadratic" -> maker-free.
#   COMPARISON the commodity ladders -- the subsidised-competitor control.
#   CONTROL    sports. Collected, NEVER quoted. It wins the uncovered table on
#              volume but is almost certainly priced off the sportsbook market,
#              so it is the negative control for the common-mode test in §1A.
#              Note KXNFLSPREAD/KXNFLTOTAL charge MAKER FEES -- only the 2nd and
#              3rd such ladders found after KXAAAGASM, and consistent with that
#              hypothesis: an exchange can tax makers where they quote anyway.
_GROUPS = json.loads((ROOT / "universe_groups.json").read_text())
PRIMARY_SERIES = sorted(_GROUPS["primary_temp"])
CONTROL_SERIES = sorted(_GROUPS["control_sports"])
COMPARISON_SERIES = [
    s for s in ALL_SERIES if s not in PRIMARY_SERIES and s not in CONTROL_SERIES
]

COLLECT_UNIVERSE = list(ALL_SERIES)

# --- sub-cent tick exclusions (measured 2026-10-18, first live cycle) --------
# The standing tick monitor fired on its first pass: KXSOLAR and KXWTIMAX quote
# on a $0.001 grid (0.1c), not the 1c grid every threshold in PROTOCOL assumes.
# This is a UNIT mismatch, not an edge judgement -- a 1c "one tick inside"
# instruction means something ten times larger on these two, and the naive
# baseline in phase 2 would not be comparable. They stay in COLLECT_UNIVERSE
# (the data is still good and the grid is worth studying); they leave the
# quoting universe until the thresholds are restated per-tick.
# Discovered BEFORE any shadow output existed. See PROTOCOL §1A Amendment 2.
SUBCENT_TICK_SERIES = ["KXSOLAR", "KXWTIMAX"]

# Quote only maker-free series; never the sports control; never a sub-cent grid.
QUOTE_UNIVERSE = [
    s
    for s in ALL_SERIES
    if s not in MAKER_FEE_SERIES
    and s not in CONTROL_SERIES
    and s not in SUBCENT_TICK_SERIES
]

# --- designated-provider control groups (PROTOCOL §4) ------------------------
# Incentivized Series list recovered in FINDINGS_PHASE0 §3. Labelled BEFORE any
# proxy output is read, which is what makes the §4 validation a real test.
LPP_KNOWN_POSITIVE = [
    "KXWTI", "KXWTIW", "KXWTIMAX", "KXWTIMIN",      # WTI — 2 providers
    "KXBRENTD", "KXBRENTMON",                        # Brent
    "KXGOLDD", "KXGOLDW", "KXGOLDMON", "KXRHGOLD",   # Gold
    "KXSILVERD", "KXSILVERW", "KXSILVERMON",         # Silver
    "KXCOPPERD", "KXCOPPERW", "KXCOPPERMON",         # Copper
    "KXNATGASD", "KXNATGASW", "KXNATGASMON",         # Gas daily & weekly
]
# Excluded from the negative control: LIP pays retail for the same behaviour the
# proxy detects, and these are the two largest ladder LIP payers (FINDINGS_LIP §3).
LPP_CONFOUNDED = ["KXAAAGASM", "KXAAAGASW"]
LPP_KNOWN_NEGATIVE = [
    s for s in ALL_SERIES
    if s not in LPP_KNOWN_POSITIVE and s not in LPP_CONFOUNDED
]

# --- collector cadence -------------------------------------------------------
# Measured 2026-10-18 against the live keyless API, 60 sequential orderbook
# requests per pacing step, all HTTP 200:
#     pause 0.22s -> 2.8 rps     pause 0.05s -> 6.0 rps
#     pause 0.10s -> 4.7 rps     pause 0.00s -> 10.1 rps
# 10 rps was clean in burst; the ladder study saw 429s near 9 rps on a sustained
# sweep, so the sustained budget below is deliberately set at roughly 60% of the
# observed burst ceiling. Raising it is a measurement, not a preference.
# MEASURED 2026-10-18 on the real universe, and the first number was wrong:
# the touch sweep over 107 series costs ~55s of a 60s cycle, leaving ~5s for
# depth. That produced 41 depth rows per cycle against 2,180 open markets -- a
# 53-MINUTE revisit, not the 3-4 min PROTOCOL §6 promises. Depth is the only
# thing we cannot reconstruct afterwards, so depth gets the cycle, not touch.
# At ~7 rps a full depth pass over 2,180 markets cannot beat ~5.2 min, so the
# cycle is set to 300s: ~55s touch, ~245s depth -> full depth pass every ~6 min.
TOUCH_PERIOD_S = 300           # full touch pass over all series, every 5 min
REQ_PAUSE_S = 0.14             # ~7 rps ceiling across both sweeps
DEPTH_BATCH_PAUSE_S = 0.14

# 1,240 open markets (measured 2026-10-18). At ~6 rps a full depth pass takes
# ~3.5 min, so depth runs as a continuous rolling sweep rather than a periodic
# one: every market is snapshotted every ~3-4 min, each row individually
# timestamped. See PROTOCOL §6.
DEPTH_MAX_LEVELS = None        # None = no truncation, both sides, all levels

# price_ranges is read per market per cycle and alarmed on change: tick_size has
# been removed from the API and other Kalshi markets now quote $0.001/$0.0001.
# A tick change silently invalidates every cent-denominated threshold.
TICK_CENTS_EXPECTED = 1.0

INCENTIVE_PERIOD_S = 86400     # /incentive_programs snapshot, daily

API_BASE = "https://api.elections.kalshi.com/trade-api/v2"
USER_AGENT = "Mozilla/5.0 (compatible; nightking-mm/1.0)"


def ensure_dirs() -> None:
    for p in (DATA, LOGS, REPORTS):
        p.mkdir(parents=True, exist_ok=True)


def killed() -> bool:
    """PROTOCOL §7: honoured within one cycle."""
    return KILL_FILE.exists()
