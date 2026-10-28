"""Long-run driver for the expanded pull: runs the unchanged wti_arb/collect.py in
batches of series, resumes by default (collect.py's manifest skips what is stored),
retries a failed batch with backoff, never exits on a transient failure.

    python3 -m waves.pull                       # main list, batches of 25
    python3 -m waves.pull --list waves_data/pull_series_commodity.txt --since 2026-09-01
    python3 -m waves.pull --pause 0.3 --batch 10

State: waves_data/pull_state.json (batches done); log: waves_data/pull.log.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WD = ROOT / "waves_data"


def log(msg):
    line = "%s %s" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with open(WD / "pull.log", "a") as f:
        f.write(line + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default=str(WD / "pull_series.txt"))
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--pause", type=float, default=0.3)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--since", default=None)
    ap.add_argument("--min-volume", type=float, default=1.0)
    ap.add_argument("--state", default=None)
    a = ap.parse_args(argv)
    series = [s.strip() for s in open(a.list) if s.strip()]
    state_p = Path(a.state or (WD / ("pull_state_%s.json" % Path(a.list).stem)))
    state = json.loads(state_p.read_text()) if state_p.exists() else {"done_batches": [], "failed": {}}
    batches = [series[i:i + a.batch] for i in range(0, len(series), a.batch)]
    log("pull start: %d series in %d batches (list %s, since %s, pause %.2f); %d batches already done" % (len(series), len(batches), a.list, a.since, a.pause, len(state["done_batches"])))
    for bi, batch in enumerate(batches):
        if bi in state["done_batches"]:
            continue
        cmd = [sys.executable, "collect.py", "--out", str(WD), "--no-probe", "--yes", "--pause", str(a.pause), "--workers", str(a.workers), "--series", ",".join(batch)]
        if a.since:
            cmd += ["--since", a.since]
        if a.min_volume:
            cmd += ["--min-volume", str(a.min_volume)]
        delay = 60
        for attempt in range(1, 7):
            log("batch %d/%d attempt %d: %s ..." % (bi + 1, len(batches), attempt, ", ".join(batch[:5])))
            t0 = time.time()
            rc = subprocess.call(cmd, cwd=str(ROOT / "wti_arb"), stdout=open(WD / "collect_stdout.log", "a"), stderr=subprocess.STDOUT)
            log("batch %d rc=%d in %.0f s" % (bi + 1, rc, time.time() - t0))
            if rc == 0:
                state["done_batches"].append(bi); break
            if rc == 1:
                # collect.py returns 1 when some markets ended in error or discovery was incomplete; a re-run resumes just those
                state["failed"][str(bi)] = state["failed"].get(str(bi), 0) + 1
                if state["failed"][str(bi)] >= 2:
                    log("batch %d: still errors after 2 passes - marking done, see manifest status=error (resume retries them later)" % (bi + 1))
                    state["done_batches"].append(bi); break
            if rc == 130:
                log("interrupted - exiting; re-run to resume"); state_p.write_text(json.dumps(state)); return 130
            log("batch %d: pausing %d s before retry" % (bi + 1, delay)); time.sleep(delay); delay = min(delay * 2, 900)
        state_p.write_text(json.dumps(state))
    log("pull finished: %d/%d batches done" % (len(state["done_batches"]), len(batches)))


if __name__ == "__main__":
    main()
