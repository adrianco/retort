---
name: update-optimal-blog
description: Refresh the data tables in optimal-blog.md from master.db. Checks the data for integrity problems FIRST, then runs the generator that picks per-language winners and splices every GEN-marked table, then reconciles the surrounding prose. Use after new experiment results land, or when the optimal-blog numbers are stale.
type: anthropic-skill
version: "1.0"
---

# Update optimal-blog.md

## Overview

`optimal-blog.md` records *what to run today*, per language and task size. Its data
tables are **not hand-written** — they are generated from `master.db` by
the `retort report optimal` subcommand (code in
[`src/retort/reporting/optimal.py`](../../src/retort/reporting/optimal.py)) and live between
`<!-- GEN:<key> START/END -->` markers. This skill is the safe procedure for refreshing
them: **check the data before you trust it**, regenerate, verify the round-trip, then fix
any prose whose numbers moved.

The order matters. master.db does **not** record the full stack/config (see the health
gaps below), so a blind regenerate can silently publish wrong numbers. Always run the
health check first and stop if it reports anything new.

## Why per-language, not aggregates

A single cross-language reliability number is misleading — it blends a stack's strong
languages with its weak ones (local Qwen passes Python/Go but fails Rust; Opus 4.8 dips on
Java). The generator's centrepiece is the **per-language success-rate matrix**; the
leading-stacks routine aggregate is explicitly labelled the least-useful number. Keep it
that way — do not "promote" an aggregate back into the recommendation.

## Steps

### 1. Health-check master.db FIRST (gate)

```bash
retort report optimal --health
```

Compare against the **known, accepted gaps** (already documented in the blog's *Keeping
this current* section):

- ⚠️ No sampling columns / `max_context_tokens` unpopulated — the qualified config is
  curated in `FEATURED_STACKS`, not filtered from data.
- ⚠️ ~250 rows have a blank `model` (local provenance bug) — attributed by experiment slug.
- ⚠️ `experiment-11`, `experiment-29` not ingested.

You MUST STOP and surface to the user if the report shows anything **beyond** those:

- **"Unmapped model strings"** — a new model appeared that no featured/legacy entry
  covers. Decide whether it's a new featured stack (add to `FEATURED_STACKS`) or legacy
  (add to `KNOWN_NONFEATURED`) before regenerating. Publishing without deciding would drop
  it silently.
- **New experiment dirs not in master.db** — results exist on disk but aren't ingested;
  the refresh would omit them. Re-ingest first, or note the omission to the user.
- A jump in the blank-model count — the harness may have regressed; a run recording no
  model is invisible to the tables. (The fix landed in `src/retort/playpen/runner.py`
  `stack_metadata()`; if new blanks appear, that path is being bypassed.)

### 2. Regenerate the tables

```bash
retort report optimal --write optimal-blog.md
```

This splices every `GEN:*` block (leading stacks, per-language matrix, per-language
winners, prompt method). It only touches text between markers.

### 3. Verify the round-trip

```bash
retort report optimal --write optimal-blog.md   # run twice
git diff --stat optimal-blog.md
```

A second `--write` MUST produce no further change — the tables are idempotent. If
`git diff` shows table cells changed, that's the real new data; if it shows nothing, the
blog was already current.

### 4. Reconcile the prose

The generator owns the tables, **not** the sentences around them. After a refresh, read
the diff and fix any prose that quotes a number that moved:

- The bullets under *Leading stacks* (e.g. "Opus 4.8 ~0.59 on hard").
- The per-language recommendation table (the curated one with the prompt/testing column)
  and its `†`/`‡` footnotes — reconcile its picks against the generated matrix and winner
  table. A cell that flipped qualified↔unqualified (e.g. a language gaining local support)
  changes the recommendation.
- The decision procedure list.
- The *language split* sentence if a language moved between local and cloud.

You MUST NOT edit numbers inside the `GEN` markers by hand — re-run the generator instead.

### 5. Report

Tell the user: which table cells changed, any prose you reconciled, and — if step 1 found
anything — what you stopped on. If nothing changed, say the blog was already current.

## Constraints Summary

- You MUST run `--health` and clear it against the known gaps **before** `--write`.
- You MUST NOT hand-edit between `GEN:*` markers; the generator is the source of truth.
- You MUST NOT introduce or re-elevate a cross-language aggregate as a recommendation —
  per-language success rates are the point.
- You MUST verify idempotency (step 3) before considering the update done.
- A new model string or un-ingested experiment is a STOP-and-ask, not a silent skip.

## Troubleshooting

**`--health` reports an unmapped model** — add it to `FEATURED_STACKS` (with a `models`
list and `short` column name) if it should appear in the blog, or to `KNOWN_NONFEATURED`
if it's legacy/a serving variant. Re-run health until only the accepted gaps remain.

**Blank-model count grew** — the harness stopped recording model for some runs. Check
`stack_metadata()` is still called by every runner's `provision()`
(`local_runner`, `metaharness_runner`, `docker_runner`); a new runner or a bypass would
reintroduce the original bug. Do not paper over it in the generator.

**A local language's number looks too low** — confirm the curated selection in
`FEATURED_STACKS` still points at the tuned-config experiments, not an all-experiment
average (which includes early bad-config runs and understates the tuned reality).
