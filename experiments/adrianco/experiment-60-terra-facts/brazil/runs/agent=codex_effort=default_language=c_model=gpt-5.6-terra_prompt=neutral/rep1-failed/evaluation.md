# Evaluation: agent=codex language=c model=gpt-5.6-terra prompt=neutral · rep 1

> **Second-opinion re-check.** A first pass recorded `requirement_coverage=None`
> with no specific findings. That under-scored the run: on inspection **all 12
> pinned capabilities are present in the code** (cited below). The genuine defect
> is *correctness*, not *coverage* — the datasets are loaded without reconciliation,
> so standings and aggregate queries are wrong. That is captured as R9 = partial
> plus supporting findings, not as wholesale missing requirements.

## Summary

- **Factors:** language=c, agent=codex, model=gpt-5.6-terra, prompt=neutral, effort=default
- **Status:** ok — builds, tests pass; correctness defect in standings/aggregates
- **Requirements:** 11/12 implemented, 1 partial (R9), 0 missing
- **Tests:** 1 C test binary passed (7 capability assertions) / 0 failed / 0 skipped — `test_coverage=1.0` (scores.json)
- **Build:** pass — `code_quality=1.0`, `defect_rate=1.0` (scores.json)
- **Lint:** pass — Makefile uses `-Wall -Wextra -Wpedantic`; `code_quality=1.0`
- **Runtime:** ok — cold start 31 ms, request median 2.2 ms (`_runtime.json`)
- **Factual accuracy:** 0.5 — 2019 Série A standings double-counted, half the clubs missing (`_factual.json`)
- **Architecture:** run-summary skill unavailable in this session; see inline notes
- **Findings:** 6 items in `findings.jsonl` (0 critical, 2 high, 3 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `main.c:18` JSON-RPC stdio loop; 5 tools at `main.c:10` |
| R2 | Loads data/kaggle/ datasets | ✓ implemented | `soccer.c:45` loads all 6 CSVs |
| R3 | Match query by team (home/away/either) | ✓ implemented | `soccer.c:50` checks both home & away |
| R4 | Filter by date range / season | ✓ implemented | `soccer.c:50` season + date_from/date_to (caveats: `R4-season`, `R4-datefmt`) |
| R5 | Filter by competition | ✓ implemented | `soccer.c:49` `comp_match`; tagged at `soccer.c:35-37` (caveat: `R5-comp`) |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `soccer.c:53` `soccer_team_record` |
| R7 | Player search by name | ✓ implemented | `soccer.c:55` `soccer_find_players` |
| R8 | Players by nationality/club + ratings | ✓ implemented | `soccer.c:55` + `main.c:15` returns overall/potential |
| R9 | Season standings from match results | ~ partial | `soccer.c:56` computes standings, but **double-counts** (`R9-dedup`) and **splits clubs by name variant** (`R9-names`) → invalid table |
| R10 | Aggregate statistical analysis | ✓ implemented | `soccer.c:53`/`soccer.c:56` aggregate over dataset (inherits inflation from R9-dedup) |
| R11 | Head-to-head between two teams | ✓ implemented | `soccer.c:54` `soccer_head_to_head` |
| R12 | Automated tests covering queries | ✓ implemented | `tests/test_soccer.c`; `test_coverage=1.0` |

**requirement_coverage = 11/12 = 0.9167** (R9 partial; all other capabilities present and exercised).

### Why R9 is partial, not missing, and not fully implemented

The standings function exists and is computed from match results (meeting the
literal `how_to_verify`), but it returns a table no reader could trust:

- **Double-counting (`R9-dedup`):** `soccer.c:45` loads five overlapping match
  files without dedup. `db.match_count == 23954` is exactly their sum
  (`4180+1337+1255+10296+6886`), and `tests/test_soccer.c:5` asserts that number —
  the test *enshrines* the un-deduplicated count. Result: `_factual.json` shows
  Atlético-MG "champion" on 96 pts (impossible in a 38-game season) and Flamengo
  listed twice at 90 pts.
- **Name-variant split (`R9-names`):** the standings key `eq_norm` (`soccer.c:48`)
  strips accents/case but **not** the `-SP`/`-RJ` state suffix, whereas
  `soccer_team_matches` (`soccer.c:47`) *does*. So "Flamengo" and "Flamengo-RJ"
  become separate rows — only 10 of 20 clubs resolve.

Both defects also inflate R6 (team records) and R11 (head-to-head), but those still
return directionally usable data; standings are qualitatively broken, so R9 alone is
marked partial.

## Build & Test

Not re-run — stored scores are authoritative (evaluate-run step 2):

```text
scores.json: test_coverage=1.0  code_quality=1.0  defect_rate=1.0  maintainability=0.667
             idiomatic=0.45  factual_accuracy=0.5  runtime=0.974
```

```text
make test  ->  tests/test_soccer  ->  "soccer tests passed"
7 assertions: db load (counts), UTF-8 normalize, team match, search_matches ordering,
team_record, head_to_head symmetry, find_players, standings ordering. 0 skipped.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 109 (main.c 18, soccer.c 57, soccer.h 34) |
| Test LOC | 5 (dense single-line) |
| Files (source, excl. data/artifacts) | main.c, soccer.c, soccer.h, tests/test_soccer.c, Makefile |
| Tools exposed | 5 (search_matches, team_statistics, head_to_head, search_players, standings) |
| Tests total / effective | 1 binary / 1 (7 assertions) |
| Skip ratio | 0% |
| Matches loaded | 23,954 (un-deduplicated) |
| Players loaded | 18,207 |
| Cold start | 31 ms; request median 2.2 ms |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [high] `R9-dedup` — standings/aggregates double-count overlapping datasets (no dedup); 23954 = sum of all 5 files.
2. [high] `R9-names` — standings key doesn't normalize state suffix; each club splits into duplicate rows.
3. [medium] `R5-comp` — BR-Football tournament strings not mapped to canonical competition names.
4. [medium] `R4-season` — BR-Football rows hardcode season=0, silently excluded from season filters.
5. [medium] `R4-datefmt` — date_from/date_to compare mixed ISO vs DD/MM/YYYY formats as raw strings.
6. [low] `bdd-norunner` — Gherkin `.feature` has no runner; only the C test executes.

## Reproduce

```bash
cd "experiments/adrianco/experiment-60-terra-facts/brazil/runs/agent=codex_effort=default_language=c_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json _factual.json _runtime.json
python3 -c "print(4180+1337+1255+10296+6886)"   # 23954 == db.match_count asserted in test
# build/test NOT re-run: stored scores.json is authoritative (test_coverage=1.0)
```
