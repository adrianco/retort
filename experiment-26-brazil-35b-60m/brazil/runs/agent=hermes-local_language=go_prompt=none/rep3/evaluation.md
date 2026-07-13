# Evaluation: agent=hermes-local · language=go · prompt=none · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local (Qwen3.6-35B-A3B), framework=unknown, prompt=none
- **Status:** **failed** — the implementation was written to a hardcoded `/tmp/brazilian-soccer-mcp/` path, entirely outside the run workspace. The archived `run_dir` contains **0 `.go` files** (only `go.mod` + `go.sum`), so the deliverable is not present, not buildable, and not reproducible.
- **Requirements:** 0/12 implemented in the archive, 0 partial, 12 missing (all R1–R12 absent from the deliverable). *The underlying code exists out-of-tree and implements most of them — see note below — but that is not part of the run.*
- **Tests:** cannot run in archive (no source). `scores.json` claims 33/34 tests via an out-of-tree build; 0 effective in the deliverable.
- **Build:** **fail** — `go build ./...` / `go test ./...` in `run_dir` error with "no Go files in directory".
- **Lint:** n/a — no source in workspace (`code_quality=1.0` in scores.json is from the out-of-tree build).
- **Architecture:** summary skipped — no source in the workspace to summarize.
- **Findings:** 4 items in `findings.jsonl` (1 critical, 2 high, 1 medium).

## What happened

`hermes-local` produced a genuinely large, mostly-correct implementation (~2,100 LOC: 19 MCP tools, all 6 CSV loaders, standings/H2H/player/stats functions, 34 unit tests, 0 skips) — but wrote every source file to the hardcoded absolute path `/tmp/brazilian-soccer-mcp/` instead of its assigned working directory. `_agent_stdout.log` confirms this: it reports editing `/tmp/brazilian-soccer-mcp/data_loader.go`, `/main.go`, `/data_loader_test.go`, and the file-mutation verifier refused two writes to "sensitive system paths" (`brazilian-soccer-mcp/go.mod` and the retort temp `data.go`). Only `go.mod`/`go.sum` (timestamp 00:54) actually landed in the workspace; everything else (README, guide, TASK.md, data/) was pre-seeded at 20:20.

Consequence: the retort scorer ran against the out-of-tree `/tmp` copy (hence `test_coverage=0.701`, `code_quality=1.0`), but the **archived run is empty of source**. The stored mechanical scores overstate the deliverable and should not be trusted for this run.

## Requirements

Assessed against the pinned `REQUIREMENTS.json` (12 requirements). All are **missing from the archived deliverable**. The parenthetical notes describe the out-of-tree `/tmp/brazilian-soccer-mcp/` code for context only — it is not part of the run.

| ID | Requirement (short) | Status (archive) | Evidence |
|----|----|----|----|
| R1 | MCP server exposing tools | ✗ missing | no `.go` in run_dir (out-of-tree: main.go registers 19 `mcp.AddTool`) |
| R2 | Load provided CSVs in data/kaggle/ | ✗ missing | (out-of-tree: data_loader.go loads all 6 CSVs) |
| R3 | Match query by team | ✗ missing | (out-of-tree: `TeamMatches`, but MCP handler hardcodes "Flamengo") |
| R4 | Filter by date range / season | ✗ missing | (out-of-tree: `SeasonMatches`) |
| R5 | Filter by competition | ✗ missing | (out-of-tree: `CompetitionMatches`) |
| R6 | Team W/L/D + goals record | ✗ missing | (out-of-tree: `CalculateTeamStats`) |
| R7 | Player search by name | ✗ missing | (out-of-tree: `SearchPlayers`) |
| R8 | Filter players by nationality/club | ✗ missing | (out-of-tree: `PlayersByClub`, `TopBrazilianPlayers`) |
| R9 | Season standings from matches | ✗ missing | (out-of-tree: `CalculateStandings`) |
| R10 | Aggregate stats | ✗ missing | (out-of-tree: `AverageGoals`, `HomeWinRate`, `BiggestWins`) |
| R11 | Head-to-head records | ✗ missing | (out-of-tree: `ComputeH2HStats`, but MCP handler hardcodes Flamengo/Palmeiras) |
| R12 | Automated tests | ✗ missing | no tests in run_dir (out-of-tree: 34 `Test*` functions, 0 skips) |

## Build & Test

```text
# in run_dir:
$ go build ./...
no Go files in .../rep3

$ go test ./...
no Go files in .../rep3
```

Stored `scores.json` (out-of-tree build, NOT the archive):
```text
test_coverage=0.701  code_quality=1.0  defect_rate=1.0  maintainability=0.428  idiomatic=0.68
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, in archive) | 0 |
| Files in archive (excl. data/) | 12 (README, guide, TASK.md, prompts.txt, go.mod, go.sum, logs, meta, scores) |
| Dependencies (go.sum) | 1 module (`modelcontextprotocol/go-sdk`) |
| Tests total (archive) | 0 |
| Tests effective (archive) | 0 |
| Skip ratio | n/a |
| Out-of-tree LOC (context only) | ~2,116 (`/tmp/brazilian-soccer-mcp/`) |

## Findings

Top items (full list in `findings.jsonl`):

1. **[critical]** No Go source in run workspace — implementation written to hardcoded `/tmp/brazilian-soccer-mcp/`; archive not buildable.
2. **[high]** All 12 requirements (R1–R12) absent from the archived deliverable.
3. **[high]** `scores.json` overstates the run — scores reflect the out-of-tree build, not the workspace.
4. **[medium]** (out-of-tree) MCP handlers ignore request parameters and hardcode team names — query interface is a fixed demo despite correct, tested underlying functions.

## Reproduce

```bash
cd experiment-26-brazil-35b-60m/brazil/runs/agent=hermes-local_language=go_prompt=none/rep3
find . -name '*.go' | wc -l            # -> 0  (no source in archive)
cat _agent_stdout.log                  # shows writes to /tmp/brazilian-soccer-mcp/*.go
cat scores.json                        # out-of-tree scores (test_coverage=0.701)
# out-of-tree remnant (not part of the run, ephemeral):
ls /tmp/brazilian-soccer-mcp/
```
