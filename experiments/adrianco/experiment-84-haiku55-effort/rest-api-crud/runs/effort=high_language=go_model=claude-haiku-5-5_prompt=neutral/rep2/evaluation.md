# Evaluation: effort=high language=go model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** build+tests passed (coverage 79.1%); 16 test functions / 0 skipped (16 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

Scores read from `scores.json` (inline gate output), not re-run:
`test_coverage=0.791`, `code_quality=1.0`, `defect_rate=1.0`, `maintainability=0.918`,
`idiomatic=0.85`, `token_efficiency=0.0186`. `defect_rate=1.0` confirms the build and
every test passed; `test_coverage` here is a coverage fraction (79.1%), not a 0/1 gate.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:44 createBook` → `store.go:60 Create`; `server_test.go:64 TestCreateAndGetBook` |
| R2 | GET /books lists all | ✓ implemented | `server.go:59 listBooks` → `store.go:91 List`; `server_test.go:157` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:60` reads query, `store.go:94` `WHERE author = ? COLLATE NOCASE`; `server_test.go:184` |
| R4 | GET /books/{id} + 404 | ✓ implemented | `server.go:70 getBook`, `store.go:79 ErrNotFound`→404; `server_test.go:210 unknown id` |
| R5 | PUT /books/{id} updates | ✓ implemented | `server.go:86 updateBook` → `store.go:122 Update`; `server_test.go:228` |
| R6 | DELETE /books/{id} | ✓ implemented | `server.go:104 deleteBook` → `store.go:141 Delete`; `server_test.go:267` |
| R7 | SQLite / embedded DB | ✓ implemented | `store.go:9` `modernc.org/sqlite` (pure-Go), `store.go:15` schema |
| R8 | JSON + appropriate codes | ✓ implemented | `server.go:171 writeJSON`; 201/200/204/400/404/422/405/503 across handlers |
| R9 | title+author required | ✓ implemented | `book.go:40-45 Validate`; rejected at `server.go:134`. Returns **422**, spec note suggests 400 — see finding |
| R10 | GET /health | ✓ implemented | `server.go:35 health` pings DB; `server_test.go:289 TestHealthCheck` (200 + 503 path) |
| R11 | README setup+run | ✓ implemented | `README.md` — Setup/Run/Test sections, flag table, full API docs |
| R12 | ≥3 tests | ✓ implemented | 16 test functions across 3 files; `defect_rate=1.0` (they ran and passed) |

No prompt-factor requirements (`prompt=neutral` carries no extra checkable instructions beyond "read TASK.md").

## Build & Test

Not re-run — stored scores used per the skill. `defect_rate=1.0` and `code_quality=1.0`
indicate `go build ./...` and `go test ./...` both succeeded and the linter was clean.
Coverage recorded at 79.1%.

```text
# would reproduce with:
go test ./...   # 16 test functions, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test .go) | 514 |
| Lines of code (tests) | 587 |
| Files (source + tests + docs) | 10 tracked (`.go` × 7, go.mod, go.sum, README.md) |
| Dependencies (direct) | 1 (`modernc.org/sqlite`); 9 indirect |
| Tests total | 16 functions (+ table subtests) |
| Tests effective | 16 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R9 — validation rejects with **422** rather than the **400** the spec's `how_to_verify` note cites. Rejection itself works (`server.go:135`), so R9 is substantively met; 422 is a defensible REST choice for validation errors, but a checker keyed on 400 would miss it.
2. [info] Implementation goes well beyond spec — graceful shutdown, ISBN check-digit validation, `Location` header, body-size cap, strict single-object JSON, 405 handling.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=high_language=go_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                  # stored mechanical scores
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rhE "^func Test" . --include="*_test.go" | wc -l        # 16 tests
go test ./...                                    # optional: re-verify build+tests
```
