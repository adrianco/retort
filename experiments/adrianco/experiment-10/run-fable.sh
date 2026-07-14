#!/usr/bin/env bash
# experiment-10 runner — Fable 5 on a single task workspace, with the toolchain
# PATH the scorer needs (go / openjdk / lein / cargo / node / python).
# Usage: run-fable.sh <brazil|bookshop>
set -euo pipefail
cd "$(dirname "$0")/.."

export PATH="/opt/homebrew/opt/openjdk/bin:/opt/homebrew/bin:$HOME/go/bin:$PATH"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home}"

task="${1:?usage: run-fable.sh <brazil|bookshop>}"
cfg="experiment-10/${task}/workspace.yaml"
design="experiment-10/${task}/design-fable.csv"
log="experiment-10/${task}/run.log"

echo "[$(date '+%F %T %Z')] starting experiment-10/${task}" | tee -a "$log"
PYTHONPATH=src .venv/bin/python -c 'from retort.cli import main; main()' \
  run --phase screening --config "$cfg" --design "$design" --resume \
  2>&1 | tee -a "$log"
echo "[$(date '+%F %T %Z')] finished experiment-10/${task} (exit ${PIPESTATUS[0]})" | tee -a "$log"
