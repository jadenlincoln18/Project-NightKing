#!/bin/bash
# Stop and remove the phase 1 launchd jobs. Does not delete data.
set -euo pipefail
UID_N=$(id -u)
for L in com.nightking.mm.collector com.nightking.mm.watchdog; do
  launchctl bootout "gui/$UID_N/$L" 2>/dev/null || true
  rm -f "$HOME/Library/LaunchAgents/$L.plist"
  echo "removed $L"
done
