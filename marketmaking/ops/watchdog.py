"""Watchdog for the phase 1 collector.

launchd's KeepAlive restarts a process that *exits*. It cannot detect one that
is alive but wedged -- a socket stuck in a read, a loop that stopped advancing.
That is the failure mode that quietly costs days of a 14-day run, so liveness
here is defined as *the heartbeat advancing*, not as the process existing.

Action on a stale heartbeat is SIGTERM: the collector flushes its buffers on
SIGTERM, and launchd then restarts it. SIGKILL is a last resort after a grace
period, and loses at most one unflushed buffer.

Logging policy (2026-10-20): EVERY check logs, including the healthy ones.
A watchdog that is silent when things are fine is indistinguishable from a
watchdog that is dead. Between 2026-10-18 and 2026-10-20 this file logged
twice in two days while running 633 times, and that silence was read as a
failure. Silence is never again evidence of health.

Escalation policy (2026-10-20): a missing or stale heartbeat raises an ALERT
to the operator, not just a kick. "No heartbeat yet" must never be a state
that can persist unnoticed for two days.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGS = pathlib.Path(os.environ.get("MM_LOGS", ROOT / "logs"))
HEARTBEAT = LOGS / "collector.heartbeat.json"
WATCHLOG = LOGS / "watchdog.log"
ALERTSTATE = LOGS / ".watchdog.alert.json"
LABEL = "com.nightking.mm.collector"

# Overridable so the kill -STOP proof can run in seconds instead of minutes.
# Production values are the defaults; the proof passes MM_STALE_S/MM_GRACE_S.
STALE_S = int(os.environ.get("MM_STALE_S", "600"))   # >2 touch cycles, >2 depth passes
GRACE_S = int(os.environ.get("MM_GRACE_S", "20"))    # SIGTERM -> SIGKILL grace

# Operator alerting.
ALERT_TARGET = os.environ.get("MM_ALERT_TARGET", "8240945418")
ALERT_CHANNEL = os.environ.get("MM_ALERT_CHANNEL", "telegram")
ALERT_REPEAT_S = int(os.environ.get("MM_ALERT_REPEAT_S", "1800"))  # re-alert every 30 min
ALERTS_ENABLED = os.environ.get("MM_ALERTS", "1") != "0"


def log(msg: str) -> None:
    line = "%s %s\n" % (dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), msg)
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(WATCHLOG, "a") as f:
        f.write(line)
    sys.stdout.write(line)


def _alert_state() -> dict:
    try:
        return json.loads(ALERTSTATE.read_text())
    except (ValueError, OSError):
        return {}


def _write_alert_state(state: dict) -> None:
    try:
        LOGS.mkdir(parents=True, exist_ok=True)
        ALERTSTATE.write_text(json.dumps(state))
    except OSError:
        pass


def alert(kind: str, msg: str) -> None:
    """Escalate to the operator, de-duplicated so a persistent fault does not spam.

    Alerts on the first occurrence of a fault kind, then at most once per
    ALERT_REPEAT_S while it persists. clear_alert() resets it.
    """
    state = _alert_state()
    now = time.time()
    last = float(state.get("last_sent", 0))
    same = state.get("kind") == kind
    if same and (now - last) < ALERT_REPEAT_S:
        log("ALERT suppressed (dedupe, %.0fs since last): %s" % (now - last, msg))
        return

    log("ALERT -> operator: %s" % msg)
    if not ALERTS_ENABLED:
        log("ALERT delivery disabled (MM_ALERTS=0)")
        _write_alert_state({"kind": kind, "last_sent": now})
        return

    exe = shutil.which("openclaw") or "/opt/homebrew/bin/openclaw"
    try:
        r = subprocess.run(
            [exe, "message", "send", "--channel", ALERT_CHANNEL,
             "--target", ALERT_TARGET, "--message", "NightKing collector: " + msg],
            capture_output=True, timeout=60,
        )
        if r.returncode == 0:
            log("ALERT delivered")
        else:
            log("ALERT delivery FAILED rc=%d %s" % (r.returncode, r.stderr.decode()[:200]))
    except Exception as e:  # delivery must never crash the watchdog
        log("ALERT delivery EXCEPTION: %s" % e)
    _write_alert_state({"kind": kind, "last_sent": now})


def clear_alert(reason: str) -> None:
    state = _alert_state()
    if state.get("kind"):
        log("recovered (%s) - clearing alert state for '%s'" % (reason, state.get("kind")))
        if ALERTS_ENABLED:
            exe = shutil.which("openclaw") or "/opt/homebrew/bin/openclaw"
            try:
                subprocess.run(
                    [exe, "message", "send", "--channel", ALERT_CHANNEL,
                     "--target", ALERT_TARGET,
                     "--message", "NightKing collector: RECOVERED - %s" % reason],
                    capture_output=True, timeout=60,
                )
            except Exception as e:
                log("recovery notice failed: %s" % e)
    _write_alert_state({})


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
        log("CHECK: no heartbeat file - kicking collector")
        alert("missing", "no heartbeat file at %s - collector kicked" % HEARTBEAT)
        kick()
        return 0

    try:
        hb = json.loads(HEARTBEAT.read_text())
    except (ValueError, OSError) as e:
        log("CHECK: unreadable heartbeat (%s) - kicking" % e)
        alert("unreadable", "heartbeat unreadable (%s) - collector kicked" % e)
        kick()
        return 0

    age = time.time() - float(hb.get("epoch", 0))
    pid = int(hb.get("pid", 0))
    sweeps = hb.get("sweeps")

    if age <= STALE_S:
        # The healthy path logs too. Silence is not health.
        log("CHECK: OK age=%.0fs (limit %ds) sweeps=%s depth_passes=%s universe=%s pid=%s"
            % (age, STALE_S, sweeps, hb.get("depth_passes"), hb.get("universe"), pid))
        clear_alert("heartbeat fresh again, age=%.0fs sweeps=%s" % (age, sweeps))
        return 0

    stale_since = dt.datetime.fromtimestamp(
        float(hb.get("epoch", 0)), dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log("CHECK: STALE heartbeat age=%.0fs (limit %ds) sweeps=%s pid=%s last_beat=%sZ"
        % (age, STALE_S, sweeps, pid, stale_since))
    alert("stale",
          "heartbeat STALE age=%.0fs (limit %ds), last beat %sZ at sweep %s. Restarting."
          % (age, STALE_S, stale_since, sweeps))

    restart_t0 = time.time()
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
    log("kickstart issued (restart handling took %.1fs)" % (time.time() - restart_t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
