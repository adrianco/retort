#!/usr/bin/env bash
# Compact progress snapshot for a running (or finished) retort experiment.
#   usage: scripts/progress.sh <experiment-dir>/<task>/retort.db [pidfile]
# Prints: liveness, cells done/total, per-stack pass tally, failure modes, red flags.
set -uo pipefail
DB="${1:?usage: progress.sh <retort.db> [pidfile]}"
PIDFILE="${2:-}"

if [ -n "$PIDFILE" ] && [ -f "$PIDFILE" ]; then
  PID=$(cat "$PIDFILE")
  if kill -0 "$PID" 2>/dev/null; then echo "STATUS: RUNNING (pid $PID)"; else echo "STATUS: NOT RUNNING"; fi
fi
[ -f "$DB" ] || { echo "  (no retort.db yet — still provisioning)"; exit 0; }

echo "--- counts ---"
sqlite3 -noheader "$DB" "SELECT '  '||status||': '||COUNT(*) FROM experiment_runs GROUP BY status;"
TOTAL=$(sqlite3 -noheader "$DB" "SELECT COUNT(*) FROM experiment_runs;")
echo "  total recorded: ${TOTAL}"

echo "--- per-stack (pass = requirement_coverage 1.0) ---"
sqlite3 -noheader "$DB" "
SELECT '  '||st||'  pass '||SUM(CASE WHEN rc>=1.0 THEN 1 ELSE 0 END)||'/'||COUNT(*)
       ||'   crashed '||SUM(CASE WHEN status='crashed' THEN 1 ELSE 0 END)
       ||'   avg '||CAST(AVG(dur) AS INT)||'s'
FROM (
  SELECT e.status,
    (SELECT fl.level_name FROM design_matrix_cells dc
       JOIN factor_levels fl ON fl.id=dc.factor_level_id AND fl.factor_name='stack'
      WHERE dc.row_id=e.design_row_id) st,
    COALESCE((SELECT value FROM run_results WHERE run_id=e.id AND metric_name='requirement_coverage'),0) rc,
    COALESCE((SELECT value FROM run_results WHERE run_id=e.id AND metric_name='_duration_seconds'),0) dur
  FROM experiment_runs e)
WHERE st IS NOT NULL GROUP BY st ORDER BY st;"

echo "--- failure modes ---"
sqlite3 -noheader "$DB" "
SELECT '  '||COUNT(*)||'x  '||substr(COALESCE(error_message,'-'),1,58)
FROM experiment_runs WHERE status IN ('crashed','failed')
GROUP BY substr(COALESCE(error_message,'-'),1,58) ORDER BY COUNT(*) DESC LIMIT 5;"

# Red flags — the harness-not-the-model signals worth surfacing early.
echo "--- red flags ---"
NOWRITE=$(sqlite3 -noheader "$DB" "SELECT COUNT(*) FROM run_results WHERE metric_name='files_written' AND value=0;" 2>/dev/null || echo 0)
ZEROQ=$(sqlite3 -noheader "$DB" "SELECT COUNT(*) FROM run_results WHERE metric_name='code_quality' AND value=0;" 2>/dev/null || echo 0)
echo "  runs that wrote NO files: ${NOWRITE:-0}   |   runs with code_quality 0: ${ZEROQ:-0}"
[ "${NOWRITE:-0}" -gt 0 ] && echo "  ^^ investigate: a blocked file tool looks identical to model incapability"
exit 0
