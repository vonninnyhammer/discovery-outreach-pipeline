#!/usr/bin/env bash
# GrantBot Pipeline — Run Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════╗"
echo "║   Opportunity Discovery & Outreach       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Ensure output dir
mkdir -p output output/drafts

# Run pipeline
python3 pipeline.py "$@"

echo ""
echo "Pipeline complete. Dashboard: output/grant_dashboard.md"
