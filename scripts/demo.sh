#!/usr/bin/env bash
# Narrated keyless demo. Pass --real to drop --mock (needs the kraken binary).
set -euo pipefail
cd "$(dirname "$0")/.."
FLAG="--mock"; [ "${1:-}" = "--real" ] && FLAG=""
python3 desk.py $FLAG demo
