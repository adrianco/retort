#!/usr/bin/env bash
# Autonomous write-up — fires AFTER the next token-window reset (>=14:00 local)
# AND the data pipeline has finished (overnight-summary.txt exists). Runs a
# headless `claude -p` to interpret results and produce the write-up.
# Fully unattended; NEVER prompts.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/opt/openjdk/bin:/opt/homebrew/bin:$HOME/go/bin:$PATH"
LOG="experiment-10/writeup.log"
echo "[$(date '+%F %T %Z')] writeup armed; waiting for >=14:00 (token reset) + overnight-summary.txt" | tee -a "$LOG"

# Wait until local time >= 14:00 AND the summary exists. Poll for up to ~10h.
for i in $(seq 1 120); do
  hour=$(date +%H)
  if [ "$hour" -ge 14 ] && [ -f experiment-10/overnight-summary.txt ]; then break; fi
  sleep 300
done
echo "[$(date '+%F %T %Z')] conditions met; launching claude -p write-up" | tee -a "$LOG"

read -r -d '' PROMPT <<'EOF'
You are resuming an unattended task in the retort repo (cwd is the repo root). The token window has reset.
Context: experiment-10 tested the new model Claude Fable 5 (claude-fable-5, priced $10/$50 per Mtok — 2x Opus 4.8,
the same per-token rate as Opus-4.8 fast mode but a distinct model the CLI prices natively). It ran on both tasks
(experiment-10/bookshop = REST-API easy, experiment-10/brazil = Brazil-soccer-MCP hard), 4 languages
(go/python/clojure/rust), 3 replicates, mirroring experiment-7 (fast mode) so cells line up 1:1 with opus-4.8
(exp-4/5/6) and opus-4.8-fast (exp-7). A pipeline already: completed the runs, ran `retort reevaluate`
(opus-4-6 spec gate -> requirement_coverage), aggregated into master.db/csv, and re-ran tooling-broken cells in
experiment-1, experiment-2, experiment-5 across all languages (clojure lein false-failures, exp-2 go, exp-1 python,
plus java/rust) under the fixed harness.

Do this, autonomously, no questions:
1. Read experiment-10/overnight-summary.txt and experiment-10/overnight.log for what completed and any failures.
2. Query experiment-10/{bookshop,brazil}/retort.db and master.csv for the Fable 5 results (status, test_coverage,
   requirement_coverage, speed, cost, code_quality per cell). Compute pass-proportion per (language,task).
3. Write experiment-10/results.md mirroring experiment-7/results.md's format: a Brazil table and a REST-API table,
   plus a short headline comparing Fable 5 vs regular opus-4.8 (exp-5/6) and opus-4.8-fast (exp-7) on the SAME cells.
   Key question: does a tier ABOVE Opus 4.8 buy any measurable reliability where 4.8 is already 1.00, given 2x cost?
   State the answer the data supports.
4. For the experiment-1/2/5 reruns: from each retort.db, report which previously-failed cells now PASS (tooling
   false-failures recovered) vs still FAIL (genuine), per language including python and go. Judge each language:
   tooling-artifact or genuine model failure? Summarize under a "Rerun outcomes" section in experiment-10/results.md.
5. Update README.md: add a claude-fable-5 row to the model reliability-vs-cost table and an experiment-10 row to the
   experiments table. Fold any recovered rerun results (exp-1/2/5) into the affected per-language/per-model tables.
   Keep prose consistent with the existing reliability-vs-cost framing.
6. Rewrite BLOG.md (the narrative companion) to incorporate Fable 5. Read the existing BLOG.md first and preserve its
   voice and structure. Weave Fable 5 into the headline reliability-vs-cost story and, near the "Fast mode" section,
   add the angle: Fable 5 is a tier ABOVE Opus 4.8 at the SAME $10/$50 rate as fast mode — does paying even more buy
   any measurable reliability where 4.8 is already 1.00? State the data-supported answer. Also fold in any rerun
   recovery (the harness-vs-model failure narrative in the "trusting your own harness" section). Do not invent
   numbers — use the measured results.
7. Commit everything (results.md, README.md, BLOG.md, code/config) on a new branch `exp-10-fable-5` with a clear
   message (do NOT push; if a git-dlp policy blocks .db files, commit the source/results/md changes and mention
   skipped .db files in the message). End the commit message with the Co-Authored-By line for Claude Opus 4.8 (1M context).
Be concise and factual; if a step's data is missing, note it in results.md rather than inventing numbers.
EOF

claude -p "$PROMPT" --dangerously-skip-permissions --max-turns 80 >>"$LOG" 2>&1
echo "[$(date '+%F %T %Z')] write-up claude -p finished (exit $?)" | tee -a "$LOG"
