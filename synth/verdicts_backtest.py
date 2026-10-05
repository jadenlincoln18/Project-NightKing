"""Fill the verdict and reading of FINDINGS_BACKTEST.md. The sentences are the author's, written after the numbers;
every number in them is read from synth/results_backtest/ so a re-render stays consistent.

    python3 -m synth.verdicts_backtest      (after synth.report_backtest)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

VERDICT_FILE = HERE / "results_backtest" / "verdict_text.md"
READING_FILE = HERE / "results_backtest" / "reading_text.md"


def main() -> int:
    from . import report_backtest
    p = ROOT / report_backtest.OUT_FILE
    s = p.read_text()
    if not VERDICT_FILE.exists() or not READING_FILE.exists():
        print("no verdict/reading text on disk yet (%s, %s)" % (VERDICT_FILE, READING_FILE))
        return 1
    V = json.load(open(HERE / "results_backtest" / "verdict.json"))
    verdict = VERDICT_FILE.read_text().strip().replace("{MECHANICAL}", V["verdict"])
    reading = READING_FILE.read_text().strip()
    kx = HERE / "results_backtest" / "kxwti_text.md"
    reading = reading.replace("{KXWTI}", kx.read_text().strip() if kx.exists() else "").replace("\n\n\n", "\n\n")
    if "**VERDICT_PLACEHOLDER**" not in s or "READING_PLACEHOLDER" not in s:
        print("placeholders absent; re-render with synth.report_backtest first")
        return 1
    s = s.replace("**VERDICT_PLACEHOLDER**", verdict).replace("READING_PLACEHOLDER", reading)
    p.write_text(s)
    print("verdict written; mechanical:", V["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
