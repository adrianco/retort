# Evaluation: language=go, model=opus-4.8, prompt=bdd · rep 1

## Summary

- **Factors:** language=go, model=opus-4.8, prompt=bdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Coverage:** test_coverage=0.703 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:handleCreate` → `store.go:Create` (INSERT) |
| R2 | GET /books lists all | ✓ implemented | `server.go:handleList` → `store.go:List` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:77` `WHERE author = ?` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `server.go:handleGet`, 404 via `ErrNotFound` (`server.go:76`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.go:handleUpdate` → `store.go:Update`, 404 on 0 rows |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `server.go:handleDelete` → `store.go:Delete`, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, schema in `migrate()` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON`/`writeError`; 201/200/204/400/404/500 used |
| R9 | Validation: title & author required | ✓ implemented | `server.go:150 validate()`; tests at `server_test.go:91,108` |
| R10 | GET /health | ✓ implemented | `server.go:handleHealth` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, env vars, API table, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 11 test funcs in `server_test.go`; test_coverage=0.703 |

### Prompt factor (bdd)

- **P1** Given/When/Then structure — ✓ 33 `// Given|When|Then` comments across tests (`server_test.go`).
- **P2** Behaviour-named tests — ✓ e.g. `Test_given_valid_book_when_created_then_status_is_201_with_assigned_id`.
- **P3** One assertion per scenario / descriptive names — ✓ largely followed; each test targets a single observable behaviour.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
code_quality      = 1.0
test_coverage     = 0.703
defect_rate       = 1.0   (build + tests passed)
maintainability   = 0.878
idiomatic         = 0.73
```

```text
go test ./...   (not re-executed)
11 BDD test functions, 0 skipped — all passing per defect_rate=1.0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, non-test) | 359 |
| Lines of code (test) | 245 |
| Go source files | 5 |
| Dependencies (go.sum lines) | 51 (1 direct: modernc.org/sqlite) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Coverage | 70.3% |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] PUT /books/{id} silently overrides any body-sent id with the path id (acceptable REST semantics) — `store.go:132`
2. [info] Strict JSON decoding via `DisallowUnknownFields` — `server.go:141`
3. [info] `SetMaxOpenConns(1)` stabilizes in-memory SQLite but serializes DB access — `store.go:27`
4. [info] Validation covers only spec-required fields (title, author) — `server.go:150`

No critical, high, or medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=go_model=opus-4.8_prompt=bdd/rep1
cat scores.json                      # mechanical scores (build/test/lint), not re-run
grep -cE "^func Test" server_test.go # 11 test functions
grep -rnE "t\.Skip" *.go             # 0 skips
go test ./...                        # optional: rebuild + run (defect_rate=1.0)
```
