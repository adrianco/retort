# Evaluation: effort=low language=go model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** build + tests pass (defect_rate=1.0); 32 test functions, 1 conditional skip (did not fire — datasets present)
- **Build:** pass (from retort.db: defect_rate=1.0, test_coverage=0.814)
- **Lint:** pass (from retort.db: code_quality=1.0; idiomatic=0.9)
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

## Requirements

Pinned list from `brazil/REQUIREMENTS.json` (R1–R12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `internal/mcp/server.go` — JSON-RPC 2.0 over stdio, `initialize`/`tools/list`/`tools/call`, protocolVersion `2024-11-05`; 7 tools registered in `tools.go:24-101` |
| R2 | Loads datasets in data/kaggle/ | ✓ implemented | `internal/data/loader.go:59` `LoadDir` reads all 6 CSVs (`loader.go:19-26`); `main.go:18` wires `-data data/kaggle` |
| R3 | Match query by team (home/away/either) | ✓ implemented | `search_matches` tool + `store.go:106` `sideMatches` honours `venue` (home/away/either) |
| R4 | Filter by date range and/or season | ✓ implemented | `store.go:66-77` season + From/To bounds; `tools.go:122` parses `from`/`to`/`season` |
| R5 | Filter by competition (Brasileirão/Copa do Brasil/Libertadores) | ✓ implemented | `store.go:59-69` competition substring fold; labels in `model.go:12-18`; `ResolveCompetition` `store.go:126` |
| R6 | Team W/L/D record + goals for/against | ✓ implemented | `team_record` tool → `stats.go:36` `TeamRecord`, `Record.add` `stats.go:21` |
| R7 | Player search by name | ✓ implemented | `search_players` `name` → `players.go:47` substring on folded name |
| R8 | Player filter by nationality/club with ratings | ✓ implemented | `players.go:50-61` club/nationality filters + Overall; `format.go:21` prints ratings |
| R9 | Season standings calculated from matches | ✓ implemented | `store.go:160` `Standings` computes pts (3/1/0) from results with tiebreakers |
| R10 | Aggregate stats (avg goals, home vs away, biggest wins) | ✓ implemented | `stats.go:123` `LeagueSummary` — GoalsPerMatch, home/draw/away rates, BiggestWins |
| R11 | Head-to-head between two teams | ✓ implemented | `head_to_head` tool → `stats.go:63` `HeadToHead` returns W/D/L + goals + recent |
| R12 | Automated tests covering query capabilities | ✓ implemented | 32 test funcs across 6 `_test.go` files; test_coverage=0.814 (>0) from retort.db |

No requirement is missing or partial. Name normalization (`internal/names`), multi-date-format parsing, and overlapping-source de-duplication are implemented beyond the literal spec (enhancements, not deductions).

## Build & Test

Scores read from `scores.json` / retort.db — toolchain not re-run per the skill.

```text
scores.json
  defect_rate     = 1.0    (build + tests succeeded)
  test_coverage   = 0.814  (Go coverage fraction; tests executed)
  code_quality    = 1.0
  idiomatic       = 0.9
  maintainability = 0.759
```

Skips: `grep -rnE "t\.Skip" --include="*.go"` → 1 hit (`internal/data/fullset_test.go:13`), a conditional guard that does **not** fire here because `data/kaggle/` is present. Effective tests = all 32 (none skipped at run time).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .go) | ~1700 |
| Lines of code (tests, .go) | 812 |
| Go files | 16 |
| Dependencies (go.sum) | 0 (stdlib only) |
| Test functions | 32 |
| Tests effective | 32 |
| Skip ratio | 0% (1 conditional guard, did not fire) |

## Findings

Full list in `findings.jsonl`:

1. [low] `TestFullDatasetPerformance` self-skips when `data/kaggle` is absent — did not fire in this archive (datasets present).

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/brazil/runs/effort=low_language=go_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go"
find . -name '*.go' -not -name '*_test.go' | xargs wc -l | tail -1
# (build/tests not re-run; scores read from scores.json per evaluate-run skill)
```
