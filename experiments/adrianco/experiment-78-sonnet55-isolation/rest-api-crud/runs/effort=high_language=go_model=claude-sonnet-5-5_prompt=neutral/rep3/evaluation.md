# Evaluation: effort=high language=go model=claude-sonnet-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=high
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** all pass / 0 failed / 0 skipped (8 test funcs + subtests, effective = all)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Coverage:** test_coverage=0.747 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 entries), used verbatim.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:73 createBook` → `store.go:57 Create`; `TestCreateAndGet` |
| R2 | GET /books lists all | ✓ implemented | `server.go:87 listBooks` → `store.go:72 List`; `TestListAndAuthorFilter` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:75-78 WHERE author = ? COLLATE NOCASE`; filter asserted in `TestListAndAuthorFilter` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `server.go:96 getBook`, `storeError` → 404; `TestBadAndMissingID` |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.go:109 updateBook` → `store.go:107 Update`; `TestUpdate` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `server.go:126 deleteBook` → `store.go:124 Delete`; `TestDelete` |
| R7 | SQLite / embedded DB | ✓ implemented | `store.go:7 modernc.org/sqlite`, on-disk `DB_PATH`; `TestPersistsOnDisk` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON` (server.go:192); 201/200/204/400/404/422/413 across handlers |
| R9 | Validation: title+author required | ✓ implemented | `server.go:44-62 validate()` → 422; `TestCreateValidation` (missing/blank cases). Uses 422 vs hint's 400 — see enh-4 |
| R10 | GET /health | ✓ implemented | `server.go:65 health` → `store.Ping`; `TestHealth` |
| R11 | README with setup/run | ✓ implemented | `README.md` Run/Test/Endpoints/Example sections |
| R12 | ≥3 tests | ✓ implemented | 8 test funcs in `server_test.go`; test_coverage=0.747 (>0) |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and only asks for tests demonstrating the requirements — satisfied by R12; no additional checkable `P*` instructions.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
defect_rate    = 1.0    (build + tests succeeded)
test_coverage  = 0.747  (tests executed; 74.7% coverage)
code_quality   = 1.0    (lint/quality)
maintainability= 0.887
idiomatic      = 0.77
```

No skipped/disabled tests: `grep -rE "t\.Skip\(|t\.Skipf\(" *.go` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, non-test) | 386 (main 51 + server 198 + store 137) |
| Lines of code (test) | 212 |
| Files (source) | 12 (incl. go.mod/go.sum/README) |
| Dependencies (direct) | 1 (`modernc.org/sqlite`; 10 incl. transitive in go.mod, 50 go.sum lines) |
| Tests total | 8 funcs (+ subtests) |
| Tests effective | 8 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 74.7% |

## Findings

Top items (all info; full list in `findings.jsonl`):

1. [info] Graceful shutdown on SIGINT/SIGTERM (main.go:38-45) — beyond spec
2. [info] Hardened request decoding: 1 MiB cap, DisallowUnknownFields, trailing-data check (server.go:141-155)
3. [info] Case-insensitive author filter backed by an index (store.go:44,76)
4. [info] Validation returns 422 where R9 how_to_verify hints 400 — semantically appropriate, R9 fully satisfied

No critical/high/medium/low findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd experiments/adrianco/experiment-78-sonnet55-isolation/rest-api-crud/runs/effort=high_language=go_model=claude-sonnet-5-5_prompt=neutral/rep3
cat scores.json                       # mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json         # pinned 12-item checklist
grep -rE "t\.Skip\(|t\.Skipf\(" *.go | wc -l   # 0 skips
wc -l *.go                            # LOC
# optional full re-verify: go test ./...
```
