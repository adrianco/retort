# Evaluation: agent=claude-code effort=high language=go model=claude-opus-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-opus-5, agent=claude-code, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 21 test functions, 0 skipped (21 effective); build + tests pass
- **Build:** pass — from `scores.json` (`defect_rate=1.0`, `test_coverage=0.766`)
- **Lint:** pass — from `scores.json` (`code_quality=1.0`, `idiomatic=0.93`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `{run_dir}/scores.json` (no re-run of build/test/lint per skill step 2):
`test_coverage=0.766`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.850`,
`idiomatic=0.93`, `token_efficiency=0.0174`.

`test_coverage=0.766` is a genuine Go coverage fraction (not the 0/1 test gate);
`defect_rate=1.0` confirms build + tests succeeded.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.go:41` `handleCreate` → `store.go:87` `Create`; returns 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `server.go:41` `handleList` → `store.go:108` `List`; empty list marshals as `[]` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `server.go:116` reads `author`; `store.go:111-114` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `server.go:42` `handleGet`; `storeError` maps `ErrNotFound`→404 (`server.go:263`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:43` `handleUpdate` → `store.go:155` `Update`; full-record replacement |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:44` `handleDelete` → `store.go:174` `Delete`; returns 204 |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:11` `modernc.org/sqlite`; schema `store.go:26`; persistence proven by `store_test.go:60` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `writeJSON`/`writeError` (`server.go:283-299`); 201/200/204/400/404/405/415/500 across handlers |
| R9 | Input validation: title and author required | ✓ implemented | `book.go:68` `Validate` → 400 (`server.go:208-216`); tested `server_test.go:138` |
| R10 | GET /health health-check endpoint | ✓ implemented | `server.go:39` `handleHealth` pings DB; 200 ok / 503 unavailable |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` (6.8 KB): setup, run, flags/env, endpoint table |
| R12 | At least 3 unit/integration tests | ✓ implemented | 21 test functions across `server_test.go` + `store_test.go`; 0 skipped |

No requirement is stubbed, partial, or missing. Several beyond-spec enhancements
(405 with `Allow` headers, JSON 404 catch-all, 1 MiB body cap, unknown-field
rejection, graceful shutdown, concurrent-write test) are noted as `info` findings.

## Build & Test

Not re-run — scores taken from `scores.json` per skill step 2.

```text
scores.json: defect_rate=1.0  test_coverage=0.766  code_quality=1.0
=> `go build` and `go test` both succeeded; 76.6% statement coverage.
```

```text
grep t.Skip / t.Skipf .go  → 0 matches   (no skipped or disabled tests)
21 Test functions, many table-driven (dozens of effective sub-cases)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, .go non-test) | 729 |
| Lines of code (tests) | 735 |
| Files (excl. .git) | 17 |
| Dependencies (go.sum lines) | 51 (1 direct: `modernc.org/sqlite`) |
| Tests total (functions) | 21 |
| Tests effective | 21 (0 skipped) |
| Skip ratio | 0% |
| Statement coverage | 76.6% |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no deductions:

1. [info] Beyond-spec robustness: 405/404 JSON handling, `Allow` headers, 1 MiB body cap
2. [info] Graceful shutdown + configurable listener (flags/env) beyond spec
3. [info] Concurrent-write and cross-restart tests directly validate the SQLite choice

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=high_language=go_model=claude-opus-5_prompt=neutral/rep1"
cat scores.json                                             # stored build/test/lint scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l  # skip count (0)
grep -rhoE "^func Test[A-Za-z0-9_]+" *.go | wc -l           # test count (21)
wc -l main.go book.go store.go server.go                    # source LOC
# (optional, would re-run toolchain — skipped per skill step 2)
# go test ./...
```
