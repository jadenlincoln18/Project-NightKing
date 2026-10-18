"""Phase 0.5 — does the fit know anything the quote does not? (PROTOCOL §1B)

This package implements §1B exactly as pre-registered in `marketmaking/PROTOCOL.md`
at commit 132ce8c, which landed before any phase 0.5 data was read. Nothing here
is free to redesign the gate: the disagreement set, the Brier/log scoring, the
event-clustered bootstrap, the "first to move" rule and the pass thresholds are
all transcriptions of that section.

Layout:
  stores.py    - locating the staged historical store; the staging gate
  disagree.py  - the §1B disagreement set
  score.py     - Brier / log score / event-clustered bootstrap (Test A)
  firstmove.py - the §1B "first to move" rule (Test B)
  testb.py     - laggard / leader classification (Test B)
  run.py       - driver

The scoring core is deliberately data-independent: it takes a tidy frame and is
tested on fixtures with known ground truth, so the pipeline can be trusted
before it is ever pointed at the real store.
"""

__all__ = ["stores", "disagree", "score", "firstmove", "testb"]
