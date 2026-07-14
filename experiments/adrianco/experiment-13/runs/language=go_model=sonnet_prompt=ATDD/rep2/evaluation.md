# Evaluation: language=go_model=sonnet_prompt=ATDD · rep 2

## Summary

- **Factors:** language=go, model=sonnet, prompt=ATDD (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented (R9 implemented but has an accuracy defect — see findings), 0 partial, 0 missing
- **Prompt (ATDD) conformance:** acceptance-test suite present and public-interface-only; one deviation (P4) — tests bind to the real dataset rather than an "empty system"
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective)
- **Build:** pass — `go test` built the module (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 0 medium, 1 low, 1 info)

Stored mechanical scores (from `scores.json`, not re-run): `test_coverage=0.84`, `code_quality=1.0`, `defect_rate=1.0`, `idiomatic=0.88`, `maintainability=0.494`, `token_efficiency=0.018`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools/handlers | ✓ implemented | `mcp/server.go:21` NewServer, `:30` Call dispatch, `:244` ServeStdio JSON-RPC, `:324` toolList (5 tools) |
| R2 | Loads provided data/kaggle CSVs | ✓ implemented | `internal/loader/loader.go:47` Load reads all 6 CSVs |
| R3 | Match by team (home/away/either) | ✓ implemented | `internal/query/query.go:138` Team filter via containsTeam (AC1, AC14) |
| R4 | Filter by date range / season | ✓ implemented | `query.go:121` Season, `:124-129` DateFrom/DateTo (AC2, AC11) |
| R5 | Filter by competition | ✓ implemented | `query.go:95` competitionMatches w/ aliases (AC3, AC14) |
| R6 | Team W/L/D + goals for/against | ✓ implemented | `query.go:208` GetTeamStats (AC4) |
| R7 | Player search by name | ✓ implemented | `query.go:264` Name filter (AC5) |
| R8 | Player filter by nationality/club + ratings | ✓ implemented | `query.go:267-272` Nationality/Club, returns overall (AC6, AC7, AC13) |
| R9 | Season standings from match results | ✓ implemented* | `query.go:288` GetStandings computes table (AC8). *Double-counts overlapping Brasileirao data — see findings |
| R10 | Aggregate statistics | ✓ implemented | `query.go:370` GetStatistics (avg goals, home win rate) (AC9) |
| R11 | Head-to-head between two teams | ✓ implemented | `query.go:165` H2H, exposed `mcp/server.go:124` head_to_head (AC12) |
| R12 | Automated tests of query capabilities | ✓ implemented | `acceptance_test.go` 15 black-box tests; test_coverage=0.84 |

### Prompt (ATDD) instructions

| ID | Instruction (short) | Status | Evidence |
|----|----|----|----|
| P1 | Requirements → executable acceptance tests as spec | ✓ implemented | `acceptance_test.go` AC1–AC15 map 1:1 to capabilities; package `main_test` |
| P2 | Test only through public interface, no back-door | ✓ implemented | `acceptance_test.go:16` call() uses only `srv.Call`; external test package, no `internal/*` access |
| P3 | Assert WHAT not HOW, domain language | ✓ implemented | Tests assert on matches/teams/goals/standings, e.g. `:205` "Flamengo as 2019 champion" |
| P4 | Each scenario from empty system, no shared data | ~ partial | `acceptance_test.go:31` every test loads the real shipped CSVs; isolated per-test but not an "empty system" |

## Build & Test

Mechanical scores were read from `scores.json` (per skill: build/test/lint are NOT re-run).

```text
go test ./...        # build + acceptance suite
defect_rate=1.0      => build + tests succeeded
test_coverage=0.84   => tests executed and passed (15 funcs, 0 skips)
```

```text
grep -rE "t\.Skip\(|t\.Skipf\(" --include=*.go  => 0   (no skipped/disabled tests)
grep -rE "^func Test" --include=*.go            => 15  (all effective)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, source only) | 1,234 |
| Lines of code (incl. acceptance_test.go) | 1,574 |
| Source files (.go) | 5 |
| Tracked files (excl. data/binary/summary) | 14 |
| Dependencies | 0 (pure stdlib; no go.sum) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [high] R9 — Standings & statistics double-count overlapping Brasileirão seasons (2019 present in both `Brasileirao_Matches.csv` and `novo_campeonato_brasileiro.csv`, both mapped to "Brasileirao Serie A"; `GetStandings`/`GetStatistics` don't dedup, unlike `FindMatches`).
2. [low] P4 — ATDD acceptance tests bind to the real dataset rather than an "empty system" as the prompt prescribes (tests are mutually independent, but coupled to dataset contents).
3. [info] ENH1 — Robustness beyond spec: multi-format date parsing, team-name normalization, extra competition mapping, full JSON-RPC stdio MCP protocol.

## Reproduce

```bash
cd experiment-13/runs/language=go_model=sonnet_prompt=ATDD/rep2
cat scores.json                                   # stored mechanical scores (no re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l
grep -rE "^func Test" . --include="*.go" | wc -l
# overlap check behind the R9 finding:
grep -c "2019" data/kaggle/Brasileirao_Matches.csv          # 380
grep -c ",2019," data/kaggle/novo_campeonato_brasileiro.csv # 380
```
