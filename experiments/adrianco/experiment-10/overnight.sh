#!/usr/bin/env bash
# Unattended orchestration — runs to completion independent of any interactive
# session or token budget. Logs everything; NEVER prompts.
#
# Pipeline:
#   1. wait for the exp-10 brazil run to finish (bookshop already done)
#   2. reevaluate exp-10 (requirement_coverage via opus-4-6 spec gate)
#   3. aggregate -> master.db/csv
#   4. rerun tooling-broken cells across exp-1/2/5 under the fixed harness:
#      every status=failed cell, PLUS completed cells that scored
#      test_coverage=0 in python/go (the languages added to the verify scope) —
#      re-marked failed so --retry-failed picks them up. Covers clojure, java,
#      rust, go (exp-2), python (exp-1). DBs backed up first.
#   5. reevaluate + re-aggregate
#   6. write experiment-10/overnight-summary.txt
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/opt/openjdk/bin:/opt/homebrew/bin:$HOME/go/bin:$PATH"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home}"

LOG="experiment-10/overnight.log"
SUMMARY="experiment-10/overnight-summary.txt"
retort() { PYTHONPATH=src .venv/bin/python -c 'from retort.cli import main; main()' "$@"; }
say() { echo "[$(date '+%F %T %Z')] $*" | tee -a "$LOG"; }

say "=== pipeline start ==="

# 1. Wait for brazil exp-10 (12 completed) — cap ~6h.
say "waiting for experiment-10/brazil to reach 12 completed runs..."
for i in $(seq 1 360); do
  n=$(sqlite3 experiment-10/brazil/retort.db "SELECT COUNT(*) FROM experiment_runs WHERE status='completed'" 2>/dev/null || echo 0)
  if [ "${n:-0}" -ge 12 ]; then say "brazil complete ($n/12)"; break; fi
  sleep 60
done

# 2. reevaluate exp-10 (spec gate -> requirement_coverage).
for sub in bookshop brazil; do
  say "reevaluate experiment-10/$sub"
  retort reevaluate --experiment-dir "experiment-10/$sub" --workers 4 >>"$LOG" 2>&1 \
    && say "  reevaluate $sub OK" || say "  reevaluate $sub FAILED (see log)"
done

# 3. aggregate
say "aggregate -> master.db/csv"
retort aggregate --csv >>"$LOG" 2>&1 && say "  aggregate OK" || say "  aggregate FAILED"

# 4. Reruns across exp-1/2/5 under the fixed harness (all languages incl python/go).
for exp in experiment-1 experiment-2 experiment-5; do
  say "=== reruns: $exp ==="
  cp "$exp/retort.db" "$exp/retort.db.pre-rerun.bak" 2>/dev/null && say "  backed up $exp/retort.db"
  # Promote completed-but-zero-coverage python/go cells to 'failed' so
  # --retry-failed re-runs them (they were never status=failed).
  marked=$(sqlite3 "$exp/retort.db" "
    UPDATE experiment_runs SET status='failed'
    WHERE status='completed'
      AND json_extract(run_config_json,'\$.language') IN ('python','go')
      AND id IN (SELECT run_id FROM run_results WHERE metric_name='test_coverage' AND value=0);
    SELECT changes();" 2>>"$LOG" | tail -1)
  say "  marked ${marked:-0} completed python/go tc=0 cells as failed for rerun"
  retort run --phase screening --config "$exp/workspace.yaml" --resume --retry-failed >>"$LOG" 2>&1 \
    && say "  $exp reruns OK" || say "  $exp reruns FAILED (see log)"
  retort reevaluate --experiment-dir "$exp" --workers 4 >>"$LOG" 2>&1 \
    && say "  $exp reevaluate OK" || say "  $exp reevaluate FAILED"
done

# 5. re-aggregate with rerun data folded in
say "re-aggregate -> master.db/csv"
retort aggregate --csv >>"$LOG" 2>&1 && say "  re-aggregate OK" || say "  re-aggregate FAILED"

# 6. summary
{
  echo "# experiment-10 overnight summary — $(date '+%F %T %Z')"
  echo
  echo "## exp-10 Fable 5 — per cell (status / test_coverage / requirement_coverage / cost)"
  for sub in bookshop brazil; do
    echo "### $sub"
    sqlite3 -header -column "experiment-10/$sub/retort.db" "
      SELECT json_extract(r.run_config_json,'\$.language') lang, r.replicate rep, r.status,
        MAX(CASE WHEN rr.metric_name='test_coverage' THEN rr.value END) testcov,
        MAX(CASE WHEN rr.metric_name='requirement_coverage' THEN rr.value END) reqcov,
        printf('%.2f',MAX(CASE WHEN rr.metric_name='_cost_usd' THEN rr.value END)) cost
      FROM experiment_runs r LEFT JOIN run_results rr ON rr.run_id=r.id
      GROUP BY r.id ORDER BY lang, rep" 2>&1
    echo
  done
  echo "## rerun experiments — status counts by language/model after rerun"
  for exp in experiment-1 experiment-2 experiment-5; do
    echo "### $exp"
    sqlite3 -header -column "$exp/retort.db" "
      SELECT json_extract(run_config_json,'\$.language') lang,
             json_extract(run_config_json,'\$.model') model, status, COUNT(*) n
      FROM experiment_runs GROUP BY lang,model,status ORDER BY lang,model,status" 2>&1
    echo
  done
} > "$SUMMARY" 2>&1
say "wrote $SUMMARY"
say "=== pipeline done ==="
