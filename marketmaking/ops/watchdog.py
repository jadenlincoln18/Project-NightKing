"""Watchdog for the phase 1 collector.

launchd's KeepAlive restarts a process that *exits*. It cannot detect one that
is alive but wedged -- a socket stuck in a read, a loop that stopped advancing.
That is the failure mode that quietly costs days of a 14-day run, so liveness
here is defined as *the heartbeat advancing*, not as the process existing.

Action on a stale heartbeat is SIGTERM: the collector flushes its buffers on
SIGTERM, and launchd then restarts it. SIGKILL is a last resort after a grace
period, and loses at most one unflushed buffer.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGS = pathlib.Path(os.environ.get("MM_LOGS", ROOT / "logs"))
HEARTBEAT = LOGS / "collector.heartbeat.json"
WATCHLOG = LOGS / "watchdog.log"
LABEL = "com.nightking.mm.collector"

STALE_S = 600        # 10 min: >2 touch cycles and >2 full depth passes
GRACE_S = 20         # SIGTERM -> SIGKILL grace


def log(msg: str) -> None:
    line = "%s %s\n" % (dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), msg)
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(WATCHLOG, "a") as f:
        f.write(line)
    sys.stdout.write(line)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def kick() -> None:
    """Ask launchd to restart the job."""
    uid = os.getuid()
    subprocess.run(["launchctl", "kickstart", "-k", "gui/%d/%s" % (uid, LABEL)],
                   capture_output=True)


def main() -> int:
    if (ROOT / "KILL").exists():
        log("KILL file present - watchdog standing down, not restarting collector")
        return 0

    if not HEARTBEAT.exists():
        log("no heartbeat file yet - kicking collector")
        kick()
        return 0

    try:
        hb = json.loads(HEARTBEAT.read_text())
    except (ValueError, OSError) as e:
        log("unreadable heartbeat (%s) - kicking" % e)
        kick()
        return 0

    age = time.time() - float(hb.get("epoch", 0))
    pid = int(hb.get("pid", 0))

    if age <= STALE_S:
        return 0

    log("STALE heartbeat: age=%.0fs (limit %ds) sweeps=%s pid=%s"
        % (age, STALE_S, hb.get("sweeps"), pid))

    if pid and alive(pid):
        log("collector pid %d alive but wedged - SIGTERM" % pid)
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            log("SIGTERM failed: %s" % e)
        for _ in range(GRACE_S):
            time.sleep(1)
            if not alive(pid):
                break
        if alive(pid):
            log("still alive after %ds - SIGKILL" % GRACE_S)
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    else:
        log("collector not running")

    kick()
    log("kickstart issued")
    return 0


if __name__ == "__main__":
    sys.exit(main())
