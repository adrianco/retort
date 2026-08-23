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
# An interactive session may have staged work. It used to be a hard refusal,
# which meant the scan lost its whole run -- including the heartbeat, whose only
# job is to make an outage visible. Since the commit below is pinned to
# `-- "$FILE"`, nothing else can ride along no matter what the index holds, so
# the guarantee is now enforced by construction rather than by giving up.
staged_other="$(git diff --cached --name-only | grep -v "^${FILE}$" || true)"
if [ -n "$staged_other" ]; then
  echo "NOTE: other files are staged by another session; committing only $FILE:" >&2
  echo "$staged_other" | sed 's/^/  /' >&2
fi

if git diff --quiet HEAD -- "$FILE"; then
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

# COMMIT FIRST, REBASE ONLY IF THE PUSH IS REJECTED.
#
# The original order was: stage -> pull --rebase --autostash -> commit -> push.
# That lost the commit every day the remote had moved and the tree was dirty.
# `--autostash` stashes the index, rebases, then pops WITHOUT `--index`, so the
# file staged a moment earlier comes back UNSTAGED; `git commit` found an empty
# index, exited 1, and `set -e` killed the script before it ever pushed. The
# pull returns 0, so the conflict check never caught it, and the edit survived
# unstaged in the working tree -- which is why 2026-08-22's heartbeat looked
# like it had simply not happened, and was later swept into an unrelated
# interactive commit instead of its own.
#
# Committing first also means the common case (remote unchanged) touches the
# remote once and never rebases at all, so a concurrent interactive session's
# index is left completely alone.
git add -- "$FILE"
if git diff --cached --quiet -- "$FILE"; then
  echo "REFUSING: $FILE did not stage; refusing to commit blind." >&2
  exit 1
fi

# A quiet day still commits, because the scan rewrites the heartbeat line on
# every run. That is the point of the heartbeat: without it a scan that finds
# nothing leaves no trace, so a silently-stopped scheduler and a slow news week
# look identical in the file. (One went unnoticed for six days from 2026-07-28.)
if [ "$n" -eq 0 ]; then
  git commit -m "scan heartbeat: no new 64GB-fittable coding models this cycle" -- "$FILE"
else
  git commit -m "candidates: ${n} new 64GB-fittable coding model(s) from daily scan" -- "$FILE"
fi
if ! git push 2>/dev/null; then
  echo "push rejected -- remote moved; rebasing onto it and retrying once." >&2
  if ! git pull --rebase --autostash; then
    echo "REFUSING: pull --rebase hit a conflict. The commit is made locally but" >&2
    echo "NOT pushed; resolve by hand and push." >&2
    git rebase --abort 2>/dev/null || true
    exit 1
  fi
  if ! git push; then
    echo "FAILED: still could not push after rebasing. Commit is local only." >&2
    exit 1
  fi
fi

if [ "$n" -eq 0 ]; then
  echo "Committed and pushed the scan heartbeat (no new candidates)."
else
  echo "Committed and pushed ${n} new candidate(s)."
fi
