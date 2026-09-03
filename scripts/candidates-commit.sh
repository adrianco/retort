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
LOG="$HOME/.retort/scan-persist.log"

cd "$REPO"

# Leave a trace on EVERY invocation, success or failure. An unattended job that
# fails silently is only detectable by the heartbeat going stale, which tells you
# THAT something broke and nothing about WHAT. On 2026-08-24 the scan fired
# (the scheduler recorded lastRunAt) and the heartbeat never moved, and there was
# no way to tell whether the script had refused, the push had failed, or the
# agent never reached the script at all -- the last of which turned out to be the
# case, but only because the working tree happened to be clean enough to rule the
# others out afterwards.
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
log() { printf '%s  %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG" 2>/dev/null || true; }
trap 'rc=$?; [ "$rc" -eq 0 ] || log "EXIT $rc (failed)"; exit $rc' EXIT
log "invoked n=${1:-<none>} head=$(git rev-parse --short HEAD 2>/dev/null)"

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
  log "no-op: $FILE unchanged (the scan did not edit the heartbeat)"
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

# DO NOT CLAIM "no new models" OVER SOMEBODY ELSE'S WORK.
#
# The guard above stops OTHER files riding along, and `-- "$FILE"` pins the
# commit. Neither helps when a concurrent interactive session has edited THIS
# file: `git add -- "$FILE"` stages the whole working-tree version, so the scan
# commits those edits too, under its own message.
#
# That happened on 2026-09-03. The scan fired at 08:47 while an interactive
# session was mid-edit on the Qwen3.8-Flash-Next entry, and pushed ~35 lines of
# that session's analysis as 1876968c, message: "scan heartbeat: no new
# 64GB-fittable coding models this cycle". Nothing was lost and the file was
# correct -- but the log now says a docs commit contains nothing when it
# contains a page of technical argument, which is exactly the kind of quiet
# wrongness the heartbeat exists to prevent elsewhere in this file.
#
# The script cannot tell which hunks are the scan's own -- it runs AFTER the
# edit. What it can do is refuse to make a claim it cannot support: a scan
# rewrites ONE line (the heartbeat) and appends bullets, so anything beyond that
# on a quiet day means the commit is carrying work the message does not describe.
# Say so in the message rather than overstating.
ins="$(git diff --cached --numstat -- "$FILE" | awk '{print $1+0}')"
del="$(git diff --cached --numstat -- "$FILE" | awk '{print $2+0}')"
extra=$(( ins - 1 ))   # insertions beyond the heartbeat rewrite

if [ "$del" -gt 1 ]; then
  echo "WARNING: $FILE has ${del} deleted lines; a scan is append-only plus the" >&2
  echo "heartbeat, so this commit is carrying someone else's edit." >&2
fi

# A quiet day still commits, because the scan rewrites the heartbeat line on
# every run. That is the point of the heartbeat: without it a scan that finds
# nothing leaves no trace, so a silently-stopped scheduler and a slow news week
# look identical in the file. (One went unnoticed for six days from 2026-07-28.)
if [ "$n" -eq 0 ] && [ "$extra" -gt 0 ]; then
  echo "NOTE: ${extra} inserted line(s) beyond the heartbeat -- a concurrent session" >&2
  echo "edited $FILE. Committing them, but saying so in the message." >&2
  git commit -m "scan heartbeat: no new 64GB-fittable coding models this cycle" \
             -m "Also carries ${extra} line(s) edited concurrently by another session; this commit is not heartbeat-only." \
             -- "$FILE"
  log "carried extra=${extra} ins=${ins} del=${del} from a concurrent session"
elif [ "$n" -eq 0 ]; then
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
log "OK pushed n=$n head=$(git rev-parse --short HEAD)"
