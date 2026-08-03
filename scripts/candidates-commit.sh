#!/usr/bin/env bash
# Persist the daily local-coding-model scan's edit to the candidate list.
#
# WHY THIS EXISTS. The scan runs unattended (~/.claude/scheduled-tasks/
# daily-local-coding-model-scan). Left to run raw git commands it stops on a
# permission prompt every morning and the scan never completes. Granting the
# agent blanket `Bash(git commit *)` / `Bash(git push)` in the USER-level
# settings would pre-approve commits and pushes in *every* repo on this machine,
# including interactive sessions -- far more authority than a docs-appending
# cron job should hold.
#
# So the scan is allowed exactly ONE command: this script. Its authority is
# bounded by what is written here, which is auditable and version-controlled.
#
# Guarantees:
#   * ONLY docs/future-experiments.md is ever staged, committed or pushed.
#   * Refuses to run if anything else is already staged (won't sweep up
#     unrelated work-in-progress from an interactive session).
#   * Aborts cleanly on a rebase conflict, leaving the working tree usable.
#   * Never force-pushes.
#
# Exit codes: 0 committed+pushed (or nothing to do), 1 refused/failed.
set -euo pipefail

REPO="/Users/adriancockcroft/code/retort"
FILE="docs/future-experiments.md"

cd "$REPO"

# Refuse if the index already holds anything else — an interactive session may
# have staged work we must not commit on its behalf.
staged_other="$(git diff --cached --name-only | grep -v "^${FILE}$" || true)"
if [ -n "$staged_other" ]; then
  echo "REFUSING: files other than $FILE are already staged:" >&2
  echo "$staged_other" >&2
  exit 1
fi

if git diff --quiet -- "$FILE" && git diff --cached --quiet -- "$FILE"; then
  echo "No change to $FILE — nothing to commit."
  exit 0
fi

n="${1:-}"
if [ -z "$n" ]; then
  echo "usage: $0 <number-of-new-candidates>" >&2
  exit 1
fi
case "$n" in
  ''|*[!0-9]*) echo "REFUSING: candidate count must be a number, got '$n'" >&2; exit 1 ;;
esac

git add -- "$FILE"

# Rebase onto origin first so the push is a fast-forward. --autostash protects
# any unrelated working-tree changes; a conflict aborts rather than resolving.
if ! git pull --rebase --autostash; then
  echo "REFUSING: pull --rebase hit a conflict; aborting and leaving the edit staged." >&2
  git rebase --abort 2>/dev/null || true
  exit 1
fi

# A quiet day still commits, because the scan rewrites the heartbeat line on
# every run. That is the point of the heartbeat: without it a scan that finds
# nothing leaves no trace, so a silently-stopped scheduler and a slow news week
# look identical in the file. (One went unnoticed for six days from 2026-07-28.)
if [ "$n" -eq 0 ]; then
  git commit -m "scan heartbeat: no new 64GB-fittable coding models this cycle"
else
  git commit -m "candidates: ${n} new 64GB-fittable coding model(s) from daily scan"
fi
git push

if [ "$n" -eq 0 ]; then
  echo "Committed and pushed the scan heartbeat (no new candidates)."
else
  echo "Committed and pushed ${n} new candidate(s)."
fi
