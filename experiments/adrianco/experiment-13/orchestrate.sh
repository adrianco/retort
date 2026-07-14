#!/usr/bin/env bash
# exp-13 orchestrator — completes the experiment to 3 replicates and writes it up.
# Sequence (unattended; never prompts):
#   1. wait for rep1 (the first 12 cells = full factor coverage) to finish
#   2. after the 3pm token reset, run replicates 2-3 across 4 parallel shards
#      (--replicates 3 --resume; the run order is replicate-major so each shard
#       fills coverage breadth-first)
#   3. once all 36 cells are in, run the post-run analysis (claude -p)
#   4. clean venv rebuild (last — both runs and analysis use the old venv)
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/opt/openjdk/bin:/opt/homebrew/bin:$HOME/go/bin:$PATH"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home}"
LOG="experiment-13/orchestrate.log"
say() { echo "[$(date '+%F %T %Z')] $*" | tee -a "$LOG"; }
rt() { PYTHONPATH=src .venv/bin/python -c 'from retort.cli import main; main()' "$@"; }
done_cells() { sqlite3 experiment-13/retort.db "SELECT COUNT(*) FROM experiment_runs WHERE status IN ('completed','failed')" 2>/dev/null || echo 0; }
say "=== finalize armed (4 shards launched manually) — waiting for all 36 cells ==="
# bash-3.2-safe: no arrays. Wait until all 36 (cell x rep) are completed/failed. Cap ~6h.
for i in $(seq 1 360); do
  n="$(done_cells)"
  [ "${n:-0}" -ge 36 ] && { say "all 36 cells in DB"; break; }
  sleep 60
done
say "total cells in DB: $(done_cells) (expect 36)"

# 3) Post-run analysis (token window already reset).
say "launching post-run analysis (claude -p)"
read -r -d '' PROMPT <<'EOF'
You are resuming an unattended task in the retort repo (cwd = repo root). The token window has reset and the
experiment-13 run is COMPLETE at 3 replicates (36 cells). exp-13 tests whether prescribing a test METHODOLOGY
changes reliability/quality on the hard Brazil task. It ran the methodology-neutral brazil fork
(github://adrianco/brazil-bench-neutral, BDD stripped) with prompt levels neutral/TDD/ATDD across
language[go,python] x model[sonnet, opus-4.8-fast], 3 replicates = 36 cells (experiment-13/retort.db). The 140
existing brazil runs (exp-2/3/4/5/7-brazil/10-brazil) are labelled prompt=BDD, so this is a four-way comparison:
BDD vs neutral vs TDD vs ATDD. Branch: exp-13-prompt-methodology.

Do this autonomously, no questions:
1. Confirm experiment-13 has 36 finished cells; read experiment-13/run.log + experiment-13/shard-*.log; note any
   failed cells and why.
2. retort reevaluate --experiment-dir experiment-13 --workers 4  (opus-4-6 spec gate -> requirement_coverage).
   Invoke via: PYTHONPATH=src .venv/bin/python -c 'from retort.cli import main; main()' reevaluate ...
3. Score ATDD methodology CONFORMANCE for the prompt=ATDD cells against experiment-13/ATDD-eval-criteria.md
   (inspect each ATDD run's archived source+tests under experiment-13/runs/, judge the 8 criteria, mean=atdd_conformance).
4. Rebuild master: PYTHONPATH=src .venv/bin/python -c 'from retort.cli import main; main()' aggregate --out master.db --csv master.csv
5. Write experiment-13/results.md: the four-way prompt comparison (BDD/neutral/TDD/ATDD) x model(sonnet,opus-4.8-fast)
   x language(go,python) with pass-proportion (requirement_coverage), test_coverage, code_quality, speed, cost. Compare
   neutral/TDD/ATDD (this run, 3 reps) against the BDD baseline (sonnet brazil=exp-2; opus-4.8-fast brazil=exp-7/brazil).
   Headline: does prescribing a test methodology (and which) measurably change reliability or quality on the hard task
   vs the neutral control? Add the ATDD-conformance findings (did the ATDD runs actually follow ATDD?). State only what
   the data supports.
6. Fill in the "## Results" section of prompt-blog.md (replace the *Pending* placeholder) with that comparison in the
   blog's first-person voice (see model-blog.md); keep the rest of prompt-blog.md.
7. Commit on branch exp-13-prompt-methodology: results.md, prompt-blog.md, scored experiment-13/retort.db, master.db/csv.
   Do NOT commit *.bak, *.log, .venv*, shard-*.log, or files >2MB other than the tracked .db/.csv. Do NOT push unless trivial.
   End the commit message with the Co-Authored-By line for Claude Opus 4.8 (1M context).
Be concise and factual; if data is missing, say so in results.md rather than inventing numbers.
EOF
claude -p "$PROMPT" --dangerously-skip-permissions --max-turns 90 >>"$LOG" 2>&1
say "analysis claude -p finished (exit $?)"

# 4) Clean venv recreate (after everything; both runs + analysis used the old venv).
say "=== recreating venv from scratch ==="
BAK=".venv.bak-$(date +%s)"; mv .venv "$BAK"
PY312="$( [ -x /opt/homebrew/opt/python@3.12/bin/python3.12 ] && echo /opt/homebrew/opt/python@3.12/bin/python3.12 || command -v python3.12 )"
"$PY312" -m venv .venv >>"$LOG" 2>&1
.venv/bin/python -m pip install -U pip -q >>"$LOG" 2>&1
if .venv/bin/python -m pip install -e ".[dev,test]" >>"$LOG" 2>&1 && PATH="$PWD/.venv/bin:$PATH" retort --version >>"$LOG" 2>&1; then
  say "venv recreate OK ($(.venv/bin/retort --version 2>&1)); running test suite"
  if .venv/bin/python -m pytest -q >>"$LOG" 2>&1; then say "test suite PASS"; else say "test suite had FAILURES (see log)"; fi
  rm -rf "$BAK"; say "clean venv in place; backup removed"
else
  say "venv recreate FAILED — restoring previous venv from $BAK"; rm -rf .venv && mv "$BAK" .venv
fi
say "=== orchestrator done ==="
