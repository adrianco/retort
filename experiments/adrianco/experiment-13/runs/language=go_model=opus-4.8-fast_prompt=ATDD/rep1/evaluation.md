# Evaluation: language=go_model=opus-4.8-fast_prompt=ATDD · rep 1

## Summary

- **Factors:** language=go, model=opus-4.8-fast, prompt=ATDD
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Prompt requirements:** 5/5 ATDD instructions followed
- **Tests:** 36 total / 1 conditional skip (35 effective in -short mode, 36 effective in full mode)
- **Build:** pass — defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see below (run-summary not invoked)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | MCP server with tools/handlers | ✓ implemented | `app.go:33` NewMCPServer, `internal/mcp/server.go` JSON-RPC 2.0, 7 tools in `registerTools()` |
| R2 | Loads datasets from data/kaggle/ | ✓ implemented | `internal/store/loader.go:15-64` Load() reads all 6 CSVs in priority order |
| R3 | Match query by team (home/away/either) | ✓ implemented | `tools.go:46-124` find_matches tool with team+venue params; `store.go:50-110` matchesFilter handles home/away/either |
| R4 | Match query by date range/season | ✓ implemented | `tools.go:76-83` season/start_date/end_date params; `store.go:62-69` date/season filtering |
| R5 | Match query by competition | ✓ implemented | `tools.go:77` competition param spans Brasileirao, Copa do Brasil, Libertadores |
| R6 | Team stats: W/L/D record and goals | ✓ implemented | `tools.go:130-187` get_team_stats returns matches/wins/draws/losses/goals_for/goals_against/points/win_rate |
| R7 | Player search by name | ✓ implemented | `tools.go:243-302` search_players with name param; `store.go:275` containsFold matching |
| R8 | Player filter by nationality/club with ratings | ✓ implemented | `tools.go:248-250` nationality/club/position params; returns overall+potential ratings |
| R9 | Standings calculated from match results | ✓ implemented | `tools.go:308-369` get_standings; `store.go:316-381` computes table with 3-1-0 points, GD tiebreak |
| R10 | Aggregate stats (avg goals, home/away, biggest wins) | ✓ implemented | `tools.go:376-444` league_stats + `tools.go:450-495` team_rankings for best home/away record |
| R11 | Head-to-head records | ✓ implemented | `tools.go:193-237` head_to_head tool; `store.go:145-173` computes from team perspective |
| R12 | Automated tests covering queries | ✓ implemented | 36 test functions: 24 acceptance (acceptance_test.go), 1 e2e (e2e_test.go), 7 unit normalize (normalize_test.go), 5 unit store (store_test.go); test_coverage=0.337 from scores.json |

## Prompt Requirements (ATDD)

| ID | Instruction | Status | Evidence |
|----|-----|-----|----|
| P1 | Acceptance tests written before implementation | ✓ implemented | `acceptance_test.go` contains 24 executable acceptance specs driving through MCP protocol |
| P2 | Exercise SUT only through public interface (MCP protocol) | ✓ implemented | `acceptance_test.go:55` startSession() uses io.Pipe, JSON-RPC 2.0 handshake; package is `app_test` (black-box) |
| P3 | Assert on WHAT not HOW, using domain language | ✓ implemented | Tests use "Flamengo", "Brasileirao", "head-to-head", "standings" — no internal structure assertions |
| P4 | Atomic and independent tests (each starts fresh) | ✓ implemented | Every test calls `newDataDir(t)`, seeds its own CSV fixtures, starts a new server instance |
| P5 | Finer-grained unit TDD underneath | ✓ implemented | `normalize_test.go` (7 tests) + `store_test.go` (5 tests) provide unit coverage below acceptance layer |

## Build & Test

```text
Build + test results from scores.json (not re-run per skill instructions):
  test_coverage = 0.337 (tests executed, 33.7% code coverage)
  code_quality  = 1.0
  defect_rate   = 1.0 (build + tests succeeded)
  maintainability = 0.605
  idiomatic     = 0.88
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go source) | 3,424 |
| Files (excl. data/) | 21 |
| Dependencies | 0 (pure stdlib) |
| Tests total | 36 |
| Tests effective | 35 (in -short mode) / 36 (full) |
| Skip ratio | 2.8% (1 conditional) |
| MCP tools registered | 7 |

## Architecture

Clean three-layer design with zero external dependencies:

1. **`cmd/bsmcp/main.go`** — CLI entry point, parses `-data` flag, wires stdin/stdout
2. **`app.go` + `tools.go`** — MCP tool registration layer; translates tool calls into domain queries; 7 tools: find_matches, get_team_stats, head_to_head, search_players, get_standings, league_stats, team_rankings
3. **`internal/mcp/server.go`** — Custom JSON-RPC 2.0 / MCP protocol server (transport-agnostic via io.Reader/Writer)
4. **`internal/store/`** — Domain engine:
   - `model.go` — Match/Player data types
   - `normalize.go` — Team name normalization, accent folding, state suffix handling, date parsing
   - `loader.go` — CSV loading with priority ordering, season-level precedence, deduplication
   - `store.go` — Query methods (filtering, aggregation, standings, rankings)

Notable design decisions:
- **Source priority**: Brasileirao_Matches.csv takes precedence over historical datasets for overlapping seasons
- **Team identity**: State codes (MG, SP, etc.) preserved in identity keys to distinguish clubs like Atletico-MG vs Atletico-GO
- **Accent-insensitive search**: foldAccents() maps Portuguese diacritics for fuzzy matching

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] TestEndToEndOverStdio conditionally skipped in -short mode
2. [medium] Test coverage score is 33.7% despite all tests passing
3. [info] Zero external dependencies — pure standard library implementation
4. [info] ATDD prompt fully followed — acceptance tests drive through MCP protocol
5. [info] Cross-file deduplication and source-priority system prevents double-counting

## Reproduce

```bash
cd experiment-13/runs/language=go_model=opus-4.8-fast_prompt=ATDD/rep1
cat scores.json
cat REQUIREMENTS.json  # (at experiment-13/REQUIREMENTS.json)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go"
grep -rE "^func Test" . --include="*.go" | wc -l
find . -name "*.go" | xargs wc -l
```
