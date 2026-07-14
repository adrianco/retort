#!/usr/bin/env bash
# One-shot migration: experiment-*/  ->  experiments/<owner>/experiment-*/
#
# Run ONLY between experiments — moving a live experiment's directory breaks the
# running process's archive writes. Verifies before and after.
#
#   usage: scripts/migrate-experiments-layout.sh [owner]   (default: adrianco)
set -euo pipefail
OWNER="${1:-adrianco}"
cd "$(git rev-parse --show-toplevel)"

# --- guard: nothing may be running -------------------------------------------
if pgrep -f "retort.cli.*run --phase" >/dev/null 2>&1 || pgrep -f "hermes --usage-file" >/dev/null 2>&1; then
  echo "REFUSING: an experiment appears to be running. Migrate between experiments." >&2
  exit 1
fi
shopt -s nullglob
EXPS=(experiment-*)
if [ ${#EXPS[@]} -eq 0 ]; then echo "nothing to migrate (already done?)"; exit 0; fi
echo "migrating ${#EXPS[@]} experiments -> experiments/$OWNER/"

BEFORE=$(python3 - <<'PY'
import sqlite3,sys
try: print(sqlite3.connect("master.db").execute("SELECT COUNT(*) FROM runs").fetchone()[0])
except Exception: print(0)
PY
)

# --- move ---------------------------------------------------------------------
mkdir -p "experiments/$OWNER"
for e in "${EXPS[@]}"; do git mv "$e" "experiments/$OWNER/$e"; done

# --- fix links ----------------------------------------------------------------
# 1. Root docs -> experiments/<owner>/experiment-NN/...
for f in README.md model-blog.md prompt-blog.md optimal-blog.md; do
  [ -f "$f" ] || continue
  perl -pi -e "s{\]\((\./)?(experiment-[0-9])}{](experiments/$OWNER/\$2}g" "$f"
done
# 2. docs/*.md use ../experiment-NN -> ../experiments/<owner>/experiment-NN
for f in docs/*.md; do
  [ -f "$f" ] || continue
  perl -pi -e "s{\]\(\.\./(experiment-[0-9])}{](../experiments/$OWNER/\$1}g" "$f"
done
# 3. Inside experiments: links OUT of the experiment tree gain 2 levels of depth.
#    (Sibling links ../experiment-NN/ still resolve and are left alone.)
find "experiments/$OWNER" -name "*.md" -print0 | xargs -0 perl -pi -e \
  's{\]\(\.\./(tasks|docs|src|scripts)/}{](../../../$1/}g'
#    ...and root-level docs (README.md, model-blog.md, ...) linked as ../README.md
find "experiments/$OWNER" -name "*.md" -print0 | xargs -0 perl -pi -e \
  's{\]\(\.\./([A-Za-z0-9._-]+\.md)}{](../../../$1}g'

# --- .gitignore ---------------------------------------------------------------
perl -pi -e 's{^(!?)experiment-\*/}{$1experiments/*/experiment-*/}' .gitignore

# --- rebuild + verify ---------------------------------------------------------
PYTHONPATH=src .venv/bin/python -c 'from retort.cli import main; main()' aggregate --out master.db >/dev/null
AFTER=$(python3 -c "import sqlite3;print(sqlite3.connect('master.db').execute('SELECT COUNT(*) FROM runs').fetchone()[0])")
echo "master.db runs: $BEFORE -> $AFTER"
[ "$AFTER" -ge "$BEFORE" ] || { echo "REGRESSION: lost runs in aggregate!" >&2; exit 1; }
python3 -c "
import sqlite3
o=sqlite3.connect('master.db').execute('SELECT owner,COUNT(*) FROM runs GROUP BY owner').fetchall()
print('attribution:', o)"

# broken relative links?
BROKEN=0
while IFS= read -r -d '' f; do
  d=$(dirname "$f")
  while read -r l; do
    case "$l" in http*|"#"*|"") continue;; esac
    t="${l%%#*}"; [ -z "$t" ] && continue
    [ -e "$d/$t" ] || { echo "  BROKEN: $f -> $l"; BROKEN=$((BROKEN+1)); }
  done < <(grep -oE '\]\([^)]+\)' "$f" | sed 's/^](//;s/)$//')
done < <(find . -name "*.md" -not -path "./experiments/*/*/runs/*" -not -path "./.git/*" -print0)
echo "broken links: $BROKEN"
[ "$BROKEN" -eq 0 ] || exit 1
echo "MIGRATION OK"
