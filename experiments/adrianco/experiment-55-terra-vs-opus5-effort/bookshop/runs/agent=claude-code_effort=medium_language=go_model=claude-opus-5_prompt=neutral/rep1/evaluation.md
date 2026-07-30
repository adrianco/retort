# Evaluation: go · claude-opus-5 · effort=medium · prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-opus-5, agent=claude-code, effort=medium, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 16 test functions, all passing / 0 failed / 0 skipped (16 effective)
- **Build:** pass — `defect_rate=1.0` from `scores.json` (build+test succeeded)
- **Lint/quality:** pass — `code_quality=1.0` from `scores.json`
- **Coverage:** `test_coverage=0.725` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:52 handleCreate`; `store.go:48 Create` INSERT |
| R2 | GET /books lists all | ✓ implemented | `server.go:71 handleList`; `store.go:65 List` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:68` `WHERE author = ? COLLATE NOCASE`; test `server_test.go:190` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `server.go:80 handleGet`; `store.go:99` maps `sql.ErrNoRows`→`ErrNotFound`→404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.go:93 handleUpdate`; `store.go:109 Update` (404 when 0 rows) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `server.go:115 handleDelete` → 204; `store.go:127 Delete` |
| R7 | Data in SQLite/embedded DB | ✓ implemented | `store.go:8` `modernc.org/sqlite`; disk round-trip test `store_test.go:68` |
| R8 | JSON responses + correct status codes | ✓ implemented | `server.go:176 writeJSON`; 201/200/204/400/404/405/503 all used |
| R9 | Validation: title & author required | ✓ implemented | `book.go:49 toBook` (trims, per-field errors); test `server_test.go:107` |
| R10 | GET /health | ✓ implemented | `server.go:41 handleHealth` (pings DB, 200/503); test `server_test.go:65` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, run, env vars, endpoint table, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 16 test functions; `test_coverage=0.725 > 0` |

No requirements missing or partial. Items beyond spec (405 handling, body-size limits,
graceful shutdown, case-insensitive filtering) noted as enhancements, not credited/deducted.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill Step 2):

```text
scores.json: test_coverage=0.725  defect_rate=1.0  code_quality=1.0
             maintainability=0.907  idiomatic=0.88  token_efficiency=0.024
defect_rate=1.0  ⇒  build + all tests passed
```

Skip scan (`grep t.Skip(` over `*.go`): 0 skipped tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. tests) | 942 |
| Source LOC (non-test) | 475 (main 59, book 85, server 188, store 143) |
| Test LOC | 467 (server_test 352, store_test 115) |
| Files (excl. .git) | 17 |
| Dependencies (direct) | 1 (`modernc.org/sqlite`); go.sum 21 lines |
| Tests total | 16 functions |
| Tests effective | 16 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 72.5% |

## Findings

Top items (full list in `findings.jsonl`) — none block conformance:

1. [low] PUT uses full-replace semantics; omitting title/author returns 400 — correct for PUT, noted for cross-run comparison.
2. [info] Test suite far exceeds the 3-test minimum (16 funcs, incl. disk-persistence test).
3. [info] Hardening beyond spec: auto-405, 1 MiB body cap, graceful shutdown.
4. [info] Coverage 72.5%; untested paths are `main()` bootstrap/shutdown wiring only.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=medium_language=go_model=claude-opus-5_prompt=neutral/rep1"
cat scores.json                                   # mechanical scores (build/test/lint)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count → 0
grep -rhE "^func Test" *_test.go | wc -l          # test count → 16
# Optional full re-run: go test ./...
```
