#!/bin/bash
# Install/refresh the phase 1 launchd jobs. Idempotent.
set -euo pipefail
REPO=/Users/patel/.openclaw/workspace/Project-NightKing
OPS="$REPO/marketmaking/ops"
LA="$HOME/Library/LaunchAgents"
UID_N=$(id -u)
mkdir -p "$LA" "$REPO/marketmaking/logs"
for L in com.nightking.mm.collector com.nightking.mm.watchdog; do
  cp "$OPS/$L.plist" "$LA/$L.plist"
  launchctl bootout "gui/$UID_N/$L" 2>/dev/null || true
  launchctl bootstrap "gui/$UID_N" "$LA/$L.plist"
  launchctl enable "gui/$UID_N/$L"
  echo "installed $L"
done
launchctl list | grep nightking || true
