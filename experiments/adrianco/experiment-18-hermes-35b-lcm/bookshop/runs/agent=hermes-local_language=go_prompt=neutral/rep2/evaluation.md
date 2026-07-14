# Evaluation: agent=hermes-local language=go prompt=neutral · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective) — `defect_rate=1.0` from `scores.json`
- **Build:** pass — from stored scores (`defect_rate=1.0`; not re-run)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see [`summary/index.md`](summary/index.md)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 2 info)

Stored mechanical scores (`scores.json`, computed at run time): test_coverage=0.683,
code_quality=1.0, defect_rate=1.0, maintainability=0.784, idiomatic=0.58,
token_efficiency=0.016. The neutral prompt factor prescribes no methodology and
adds no additional checkable requirements, so the checklist is TASK.md's 12 pinned
requirements only.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title,author,year,isbn) | ✓ implemented | `handlers.go:74` HandleCreateBook → `database.go:57` CreateBook; test `TestCreateBookSuccess` |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:117` HandleListBooks → `database.go:83` GetAllBooks; test `TestListBooksReturnsAll` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `database.go:87-89` WHERE author LIKE; test `TestListBooksFilterByAuthor` (substring match — see F2) |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `handlers.go:145` HandleGetBook; `database.go:126` ErrNoRows→404; tests `TestGetBookSuccess`/`TestGetBookNotFound` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:175` HandleUpdateBook → `database.go:136` UpdateBook; tests `TestUpdateBookSuccess`/`TestUpdateBookPartial` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:215` HandleDeleteBook → `database.go:180` DeleteBook (404 when 0 rows); tests `TestDeleteBookSuccess`/`TestDeleteBookNotFound` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `database.go:8` `modernc.org/sqlite`, `database.go:34-51` createTables (real INSERT/SELECT, not in-memory maps) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/404/400/204/500 set explicitly across `handlers.go`; Content-Type application/json |
| R9 | Validation: title and author required | ✓ implemented | `handlers.go:243` validateCreate; tests `TestCreateBookMissingTitle`/`MissingAuthor`/`EmptyTitleAndAuthor` (update path not validated — see F1) |
| R10 | GET /health health-check | ✓ implemented | `handlers.go:21` HandleHealth returns `{status:"ok",...}`; test `TestHealthCheck` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — prerequisites, `go mod download`, `go run .`, env vars, curl examples, testing |
| R12 | At least 3 unit/integration tests | ✓ implemented | 17 `Test*` funcs in `handler_test.go`; test_coverage=0.683 (>0) |

## Build & Test

Build/test/lint were **not re-run** — stored scores from `scores.json` are authoritative.

```text
scores.json: {"code_quality": 1.0, "test_coverage": 0.683, "defect_rate": 1.0,
              "maintainability": 0.784, "idiomatic": 0.58, "token_efficiency": 0.016}
defect_rate=1.0  ⇒ build + tests succeeded
code_quality=1.0 ⇒ lint clean
```

```text
go test ./...   (per _agent_stdout.log: "Tests: 17/17 passing")
17 Test* functions, 0 t.Skip / t.Skipf  → 17 effective, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (all .go) | 1068 |
| Lines of code (non-test .go) | 538 |
| Files (excl. .git) | 16 |
| Dependencies (go.sum lines) | 41 |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [medium] F1 — PUT /books/{id} performs no validation; a partial update can blank a required title/author (`handlers.go:175`, `database.go:149-160`).
2. [low] F2 — `?author=` filter uses substring `LIKE '%...%'` rather than exact match (`database.go:88-89`).
3. [low] F3 — `doRequest` test helper double-invokes handlers for `/health` (`handler_test.go:36-40`).
4. [info] F4 — Health timestamp is a Unix-epoch string, not RFC3339 (`handlers.go:29`).
5. [info] F5 — Enhancement: partial-update via pointer DTO fields, beyond spec (`model.go:25-30`).

No critical or high findings: all 12 pinned requirements implemented, build+tests pass, lint clean.

## Reproduce

```bash
cd experiment-18-hermes-35b-lcm/bookshop/runs/agent=hermes-local_language=go_prompt=neutral/rep2
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -cE "^func Test" handler_test.go  # 17 tests
grep -rEc "t\.Skip\(|t\.Skipf\(" . --include="*.go"  # 0 skips
# (build/test/lint intentionally NOT re-run — scores.json is authoritative)
```
