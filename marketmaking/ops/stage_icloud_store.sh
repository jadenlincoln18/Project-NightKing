#!/bin/sh
# Resume staging the historical Kalshi store out of iCloud Drive into
# marketmaking/data/_import/waves_data/. Idempotent: anything already present
# and non-empty at the destination is skipped, so re-running costs only a scan.
#
# Why this script exists (do not re-derive, both cost real time on 2026-10-20):
#
#   1. `brctl download` SILENTLY NO-OPS ON A RELATIVE PATH. It returns rc=0,
#      prints nothing, and the file stays `dataless`. Only an ABSOLUTE path
#      queues the fetch. (This is the second half of the "brctl download <dir>
#      does not recurse" gotcha already recorded in STATE.md.)
#
#   2. REQUEST AND COPY MUST BE DECOUPLED. Materialisation is asynchronous and
#      the daemon re-evicts. A request-sleep-copy loop misses every file that
#      lands mid-sleep. This script runs the copier as a tight inner loop over
#      the whole list and re-requests only what is still missing, in bounded
#      chunks so the daemon can drain instead of being reset.
#
#   3. Copy out the instant a file is readable. Bytes on local disk cannot be
#      evicted; bytes in iCloud can, and are.
#
# Known limit: iCloud throttles. On 2026-10-20 it served ~573-619 KB/s for about
# an hour (6,323 of 12,914 files) and then stopped honouring requests entirely,
# including single explicit absolute-path calls with every local loop stopped.
# That is a server-side state, not a bug here. Leave it an hour and re-run.
#
# Usage:  sh marketmaking/ops/stage_icloud_store.sh [max_rounds]

set -u

SRC="${NK_ICLOUD_SRC:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/Desktop/Project-NightKing/waves_data/parquet}"
HERE=$(cd "$(dirname "$0")" && pwd)
DST="${NK_STAGE_DST:-$HERE/../data/_import/waves_data/parquet}"
ROUNDS="${1:-40}"
WORK="${TMPDIR:-/tmp}/nk_stage"

mkdir -p "$WORK"

if [ ! -d "$SRC" ]; then
  echo "source not found: $SRC" >&2
  exit 1
fi

# --- the scope: PROTOCOL 1A primary universe + the commodity comparison group.
# Deliberately NOT all 422 series in the store.
if [ ! -s "$WORK/files.txt" ]; then
  echo "enumerating target series..."
  : > "$WORK/series.txt"
  ls "$SRC/kalshi_candles/period=1/" | grep -E '^series=(KXHIGH|KXLOW)' >> "$WORK/series.txt"
  for s in KXWTI KXWTIW KXBRENTD KXGOLDD KXNATGASD; do echo "series=$s"; done >> "$WORK/series.txt"
  : > "$WORK/files.txt"
  while IFS= read -r s; do
    ( cd "$SRC" && find "kalshi_candles/period=1/$s" -type f -name '*.parquet' 2>/dev/null ) >> "$WORK/files.txt"
    ( cd "$SRC" && find "kalshi_markets/$s" -type f -name '*.parquet' 2>/dev/null ) >> "$WORK/files.txt"
  done < "$WORK/series.txt"
fi

total=$(wc -l < "$WORK/files.txt" | tr -d ' ')
echo "target: $total files across $(wc -l < "$WORK/series.txt" | tr -d ' ') series"

for round in $(seq 1 "$ROUNDS"); do
  # copy anything already readable, first and every round
  copied=0
  : > "$WORK/miss.txt"
  while IFS= read -r rel; do
    d="$DST/$rel"
    if [ -s "$d" ]; then continue; fi
    s="$SRC/$rel"
    if head -c 1 "$s" >/dev/null 2>&1; then
      mkdir -p "$(dirname "$d")"
      cp "$s" "$d" 2>/dev/null && copied=$((copied + 1)) && continue
    fi
    printf '%s\n' "$SRC/$rel" >> "$WORK/miss.txt"
  done < "$WORK/files.txt"

  missing=$(wc -l < "$WORK/miss.txt" | tr -d ' ')
  echo "round=$round copied=$copied staged=$((total - missing))/$total"
  if [ "$missing" -eq 0 ]; then echo "STAGING COMPLETE"; break; fi

  # request a bounded chunk, ABSOLUTE paths only
  head -800 "$WORK/miss.txt" | xargs -P 12 -I{} brctl download "{}"
  sleep 20
done

echo "done. verify with:"
echo "  ../.venv/bin/python -c 'from phase05 import stores; print(stores.check_staging())'"
