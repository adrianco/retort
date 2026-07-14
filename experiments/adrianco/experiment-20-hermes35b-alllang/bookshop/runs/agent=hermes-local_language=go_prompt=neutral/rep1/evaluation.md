# Evaluation: agent=hermes-local language=go prompt=neutral · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local (model Qwen3.6-35B-A3B), framework=unknown (gorilla/mux), prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective) — from `defect_rate=1.0`, `test_coverage=0.68` in scores.json
- **Build:** pass (implied by `defect_rate=1.0`; the compiled `bookapi` binary is present)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:35 CreateBook` → `database.go:54 CreateBook`; `main.go:28` |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:62 ListBooks` → `database.go:89`; `main.go:29` |
| R3 | GET /books ?author= filter | ✓ implemented | `handlers.go:63-67` reads `author`; `database.go:93 WHERE author = ?`; `TestListBooks_FilterByAuthor` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `handlers.go:79 GetBook`; 404 at `handlers.go:89`; `TestGetBook_NotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:97 UpdateBook` → `database.go:125` partial update; `TestUpdateBook_Success` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:132 DeleteBook` → `database.go:170`; `TestDeleteBook_Success` |
| R7 | SQLite / embedded DB | ✓ implemented | `database.go:9,19` mattn/go-sqlite3, real file/`:memory:` store |
| R8 | JSON responses + proper status codes | ✓ implemented | `writeJSON` `handlers.go:18`; 201/200/204/400/404/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `handlers.go:43-50`; `TestCreateBook_MissingTitle`/`MissingAuthor` |
| R10 | GET /health | ✓ implemented | `handlers.go:30 HealthCheck`; `TestHealthCheck` |
| R11 | README with setup/run | ✓ implemented | `README.md` — endpoints, setup, curl examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 14 test funcs in `handlers_test.go`; `test_coverage=0.68 > 0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
scores.json: {"code_quality":1.0, "test_coverage":0.68, "defect_rate":1.0,
              "maintainability":0.853, "idiomatic":0.58, "token_efficiency":0.0176}
```

`defect_rate=1.0` ⇒ `go build` + `go test` succeeded; `test_coverage=0.68` ⇒ ~68% statement coverage with all tests passing. `code_quality=1.0` ⇒ clean lint. No skipped tests (`grep t.Skip` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, .go excl. test) | 433 (main 43, models 35, handlers 152, database 203) |
| Test LOC | 431 |
| Files (excl. binary/DB artifacts) | 6 source (5 .go + README) |
| Dependencies (go.sum lines) | 4 (gorilla/mux, mattn/go-sqlite3) |
| Tests total / effective | 14 / 14 |
| Skip ratio | 0% |
| Coverage | 68% |

## Findings

Full list in `findings.jsonl`:

1. [low] Stored timestamps may deserialize to zero time on read — `database.go:196` layout mismatch vs go-sqlite3 storage format, parse error discarded.
2. [info] created_at/updated_at tracked beyond spec (enhancement).

No critical/high/medium findings. All 12 pinned requirements implemented; build, tests, and lint pass.

## Reproduce

```bash
cd experiment-20-hermes35b-alllang/bookshop/runs/agent=hermes-local_language=go_prompt=neutral/rep1
cat scores.json                                  # mechanical scores (not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" handlers_test.go           # 14 test funcs
# optional full re-run:
go test ./... -cover
```
