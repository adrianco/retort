# Evaluation: language=go · model=opus · tooling=beads · rep 1

## Summary

- **Factors:** language=go, model=opus, tooling=beads (DB run_config also records prompt=BDD)
- **Status:** **failed** — module does not compile. The `internal/data` package, imported by all 9 source files, is absent from the archive, so nothing builds and no test executes (`test_coverage=0.0` in `scores.json`).
- **Requirements:** 0/12 verifiably implemented · 1 partial (R12) · 1 missing (R2) · 10 cannot-verify (R1, R3–R11 — source logic present but unbuildable)
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective) — 11 `Test*` functions exist but the packages fail to build (`[setup failed]`)
- **Build:** **fail** — `package brsoccer/internal/data is not in std`; also incomplete `go.sum` (missing `golang.org/x/text`)
- **Lint:** unavailable — cannot lint code that does not compile
- **Architecture:** summarized inline below (`run-summary` not invoked for a non-compiling run)
- **Findings:** 7 items in `findings.jsonl` (1 critical, 3 high, 1 medium, 2 info)

> **Note on stored scores.** `scores.json` is all-zeros and matches the archived (broken) state. The `retort.db` row for this cell (run id 14, status=completed) instead shows `test_coverage=0.333`, `code_quality=1.0`, `defect_rate=1.0`, `requirement_coverage=0.9167` — but that row was scored against a *different, complete* workspace (run_config includes `prompt=BDD`) that still had the `internal/data` package. The archive on disk is missing that package, so the DB scores do **not** describe what is in this directory. This evaluation reflects the archived files as they actually exist, verified by re-running `go build`/`go test`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing query tools | ? cannot-verify | `internal/mcp/server.go` (JSON-RPC stdio), `tools.go:14` registers 8 tools — but build fails |
| R2 | Load datasets in data/kaggle/ | ✗ missing | `main.go:16` calls `data.Load` but `internal/data` pkg + `data/` dir absent |
| R3 | Match query by team (home/away/either) | ? cannot-verify | `internal/query/match.go:44-48` `Team` filter (home OR away) |
| R4 | Match query by date range / season | ? cannot-verify | `match.go:26,32-37` `Season`/`From`/`To` filters |
| R5 | Match query by competition | ? cannot-verify | `match.go:29` competition substring filter |
| R6 | Team W/L/D record + goals | ? cannot-verify | `internal/query/team.go:35` `ComputeTeamStats` |
| R7 | Player search by name | ? cannot-verify | `internal/query/player.go:22` name contains-fold |
| R8 | Player filter by nationality/club + ratings | ? cannot-verify | `player.go:25-34` nationality/club/min_overall |
| R9 | Standings computed from matches | ? cannot-verify | `team.go:78` `Standings` (points/GD from results) |
| R10 | Aggregate statistics | ? cannot-verify | `internal/query/stats.go:19` `Overall` + `BiggestWins` |
| R11 | Head-to-head between two teams | ? cannot-verify | `match.go:76` `H2H` |
| R12 | Automated tests covering queries | ~ partial | 11 BDD-style tests in `query_test.go`/`server_test.go`, but they **do not execute** (build fails, `test_coverage=0`) |

`?` cannot-verify is used per the evaluate-run rule that, when `test_coverage==0`, requirements whose runtime behavior cannot be confirmed are not credited as implemented. The source logic for these 10 looks correct on read; it is simply unbuildable.

## Build & Test

```text
$ go build ./...
cmd/brsoccer-mcp/main.go:8:2: package brsoccer/internal/data is not in std
  (/opt/homebrew/Cellar/go/1.26.3/libexec/src/brsoccer/internal/data)
# (also, with the package present, build would still need go.sum:)
golang.org/x/text@v0.36.0: missing go.sum entry for go.mod file
```

```text
$ go test ./...
# brsoccer/cmd/brsoccer-mcp
cmd/brsoccer-mcp/main.go:8:2: package brsoccer/internal/data is not in std
FAIL	brsoccer/cmd/brsoccer-mcp [setup failed]
FAIL	brsoccer/internal/mcp   [setup failed]
FAIL	brsoccer/internal/query [setup failed]
FAIL
```

## Architecture (inline)

- `cmd/brsoccer-mcp/main.go` — entrypoint: `data.Load(dir)` → `mcp.NewServer` → `RegisterSoccerTools` → serve stdio.
- `internal/mcp/server.go` — minimal JSON-RPC 2.0 / MCP server over ndjson stdio (initialize, tools/list, tools/call, ping).
- `internal/mcp/tools.go` — registers 8 tools wiring args → `internal/query` functions; `format.go` formats results.
- `internal/query/{match,team,player,stats}.go` — pure query logic over `data.DB` (filters, aggregations, standings, H2H).
- `internal/data/` — **MISSING**: should define `DB`, `Match`, `Player`, `Load`, `TeamMatches`, `NormalizeTeam`. Its absence breaks every package.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of Go (source + tests) | 1,165 |
| Files (excl. .git) | 23 |
| Go source files | 10 (incl. 2 test files); 1 package missing |
| Dependencies | 1 declared (`golang.org/x/text`), `go.sum` incomplete |
| Tests total (written) | 11 |
| Tests effective (executed) | 0 |
| Skip ratio | 0% (no `t.Skip`) — but 0 run |
| Build | fail |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. **[critical]** Module does not compile — `internal/data` package absent (`build-fail`)
2. **[high]** R2 data-loading layer absent — CSVs never read (`R2`)
3. **[high]** All test packages fail to build — 0 effective tests (`test-fail`)
4. **[high]** Test suite written but does not execute (`R12`)
5. **[medium]** Incomplete `go.sum` — missing `golang.org/x/text` checksum (`build-gosum`)

## Reproduce

```bash
cd experiment-2/runs/language=go_model=opus_tooling=beads/rep1
go build ./...                      # fails: package brsoccer/internal/data is not in std
go test ./...                       # FAIL ... [setup failed] x3
grep -rl "brsoccer/internal/data" --include="*.go" .   # 9 files import the missing package
ls internal/data 2>&1               # No such file or directory
cat scores.json                     # all 0.0 — consistent with build failure
```
