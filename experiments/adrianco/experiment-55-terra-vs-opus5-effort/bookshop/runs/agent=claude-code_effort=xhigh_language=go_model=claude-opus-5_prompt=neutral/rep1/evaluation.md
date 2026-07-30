# Evaluation: go · claude-code · claude-opus-5 · effort=xhigh · prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-opus-5, agent=claude-code, effort=xhigh, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 40 test functions (16 subtests) — passed / 0 failed / 0 skipped (all effective)
- **Build:** pass — `defect_rate=1.0` from `scores.json` (build + tests succeeded)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores (from `scores.json`): `test_coverage=0.866` (statement-coverage fraction; tests executed and passed), `defect_rate=1.0` (build+test succeeded), `code_quality=1.0`, `maintainability=0.876`, `idiomatic=0.89`, `token_efficiency=0.0080`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `internal/api/handlers.go:47` → `internal/books/store.go:106` INSERT; test `api_test.go:144 TestBookLifecycle` |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:69`; `store.go:148 List`; test `TestBookLifecycle`, `TestListFiltersByAuthor` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `store.go:151` WHERE author COLLATE NOCASE; `handlers.go:70` rejects unknown params; test `api_test.go:431 TestListFiltersByAuthor` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `handlers.go:84`; `store.go:131 Get`→ErrNotFound; test `TestRoutingAndMethodErrors` (unknown id → 404) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:101`; `store.go:180 Update` (tx, replace-all); test `api_test.go:508 TestUpdateReplacesWholeRecord` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:127`; `store.go:217 Delete`→204/404; test `TestBookLifecycle` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:11` modernc.org/sqlite; `store.go:30` schema; test `store_test.go TestStorePersistsAcrossRestart` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `respond.go:40 respond` sets JSON; 201/200/204/404/409/415/422/405 used; test `TestMalformedRequestsAreRejected`, `TestRoutingAndMethodErrors` |
| R9 | Validation: title & author required | ✓ implemented | `internal/books/book.go:73 Validate` rejects empty title/author; test `api_test.go:222 TestCreateRejectsInvalidFields` (returns 422 — see finding) |
| R10 | GET /health health check | ✓ implemented | `handlers.go:31 handleHealth` pings DB → 200/503; test `api_test.go:583 TestHealthReportsReady`, `TestHealthReportsDatabaseFailure` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md:13` Quick start (`go run .`, `go test ./...`), Configuration, API, curl examples |
| R12 | >= 3 unit/integration tests | ✓ implemented | 40 test functions across 5 `_test.go` files; `test_coverage=0.866 > 0` |

No `prompt`-factor `P*` requirements: `prompt=neutral` is the default framing, not an added instruction file.

## Build & Test

Not re-run — stored scores are authoritative per the skill (compiled-language re-run is pure duplication).

```text
scores.json: defect_rate=1.0  → build + test succeeded
scores.json: test_coverage=0.866 → tests executed and passed (statement coverage ~86%)
scores.json: code_quality=1.0
grep t.Skip → 0 skipped tests
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, .go non-test) | 1123 |
| Lines of code (tests) | 1573 |
| Go source files | 14 (9 source + 5 test) |
| Dependencies (go.sum lines) | 51 (1 direct: modernc.org/sqlite) |
| Tests total (functions) | 40 (+16 subtests) |
| Tests effective | 40 (0 skipped) |
| Skip ratio | 0% |
| Build duration | not re-run (stored scores used) |

## Findings

All 4 findings are informational (enhancements / a defensible status-code choice); none affect conformance. Full list in `findings.jsonl`:

1. [info] Validation failures return 422 rather than the 400 the checklist notes — RFC-compliant and more precise; R9 still satisfied (requests are rejected).
2. [info] Strict request decoding (content-type, unknown-field, single-object, 64KiB cap) beyond spec.
3. [info] ISBN-10/13 check-digit validation + canonical-form uniqueness (409 on conflict).
4. [info] Panic-recovery + access-logging middleware, graceful shutdown, DB-backed health check.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=xhigh_language=go_model=claude-opus-5_prompt=neutral/rep1"
cat scores.json                                             # stored mechanical scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l  # 0 skips
grep -rhoE "^func Test\w+" . --include="*_test.go" | wc -l  # 40 test funcs
# Optional full re-run (not required — stored scores are authoritative):
go test ./...
```
