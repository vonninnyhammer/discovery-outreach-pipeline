#!/usr/bin/env bash
# GrantBot — Hermes Cron Runner
# Usage: ./cron_run.sh [--full | --discover-only | --status]
#
# Runs the pipeline in the background and logs output.
# Designed for cron scheduling or manual invocation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:---full}"
LOG_DIR="$SCRIPT_DIR/output/logs"
LOG_FILE="$LOG_DIR/run_$(date +%Y%m%d_%H%M%S).log"
LOCK_FILE="/tmp/grantbot.lock"

mkdir -p "$LOG_DIR"

# Prevent concurrent runs
if [ -f "$LOCK_FILE" ]; then
    pid=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo "Pipeline already running (PID: $pid). Exiting."
        exit 0
    fi
    rm -f "$LOCK_FILE"
fi

echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

case "$MODE" in
    --full)
        echo "[$(date -Iseconds)] Running full pipeline..."
        python3 pipeline.py 2>&1 | tee "$LOG_FILE"
        ;;
    --discover-only)
        echo "[$(date -Iseconds)] Running discovery only..."
        python3 -c "
import asyncio, sys, json
sys.path.insert(0, '$SCRIPT_DIR')
from discover import discover_all
from filter import filter_and_score
grants = asyncio.run(discover_all())
qualified = filter_and_score(grants)
print(json.dumps([g.to_dict() for g in qualified[:20]], indent=2))
" 2>&1 | tee "$LOG_FILE"
        ;;
    --status)
        echo "=== GrantBot Pipeline Status ==="
        echo "Last run: $(ls -t output/logs/run_*.log 2>/dev/null | head -1 || echo 'Never')"
        echo "Dashboard: $(ls -la output/grant_dashboard.md 2>/dev/null || echo 'Not generated')"
        echo "Grants DB: $(wc -l < output/grants_db.json 2>/dev/null || echo 0) entries"
        echo "Drafts: $(ls output/drafts/*.md 2>/dev/null | wc -l) files"
        echo "ICS: $(ls -la output/grant_deadlines.ics 2>/dev/null || echo 'Not generated')"
        ;;
    *)
        echo "Usage: $0 [--full | --discover-only | --status]"
        exit 1
        ;;
esac

echo "[$(date -Iseconds)] Done. Log: $LOG_FILE"
