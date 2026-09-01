# Evaluation: effort=default_language=go_model=claude-fable-5-1_prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-fable-5-1, prompt=neutral, effort=default (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 10 test functions, all passing / 0 failed / 0 skipped (10 effective) — `defect_rate=1.0` from scores.json
- **Build:** pass — `defect_rate=1.0` (build+test gate); not re-run
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** run-summary skill unavailable this session (see Findings)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

Stored scores (scores.json): `code_quality=1.0`, `test_coverage=0.792`, `defect_rate=1.0`, `maintainability=0.80`, `idiomatic=0.87`, `token_efficiency=0.026`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `handlers.go:240 handleCreate` → `store.go:122 Create`; test `api_test.go:92` |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:259 handleList` → `store.go:155 List`; test `api_test.go:207` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `handlers.go:260` reads `author`; `store.go:158` `WHERE author = ? COLLATE NOCASE`; test `api_test.go:236` |
| R4 | GET /books/{id} returns one book (404 absent) | ✓ implemented | `handlers.go:269 handleGet`; `ErrNotFound`→404 `handlers.go:221`; test `api_test.go:328` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:282 handleUpdate` → `store.go:182 Update`; test `api_test.go:259` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:304 handleDelete` → `store.go:204 Delete` (204/404); test `api_test.go:297` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:11` `modernc.org/sqlite`, `store.go:68 migrate` schema; persistence test `api_test.go:356` |
| R8 | JSON responses + appropriate HTTP status codes | ✓ implemented | `handlers.go:69 writeJSON`; 201/200/204/400/404/409/415/422/503 used across handlers |
| R9 | Input validation: title & author required | ✓ implemented | `handlers.go:114 validateBookInput` rejects blank/missing; test `api_test.go:131`. Note: returns **422** not the literal 400 (see findings) |
| R10 | GET /health endpoint | ✓ implemented | `handlers.go:232 handleHealth` pings DB; test `api_test.go:74` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — Setup and run, endpoints, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 10 `func Test*` in `api_test.go`; 0 skips |

Enhancements beyond spec (not deductions): ISBN-10/13 checksum validation, duplicate-ISBN 409 conflict, `Location` header on create, graceful shutdown, request logging, body-size limit, `DisallowUnknownFields`, 415 on wrong Content-Type, case-insensitive author filter.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: defect_rate=1.0  (build + tests passed)
scores.json: code_quality=1.0 (lint clean)
scores.json: test_coverage=0.792 (coverage fraction)
```

```text
go test ./...  (not re-run)
10 test functions, 0 t.Skip — TestHealth, TestCreateAndGetBook, TestCreateValidation,
TestListWithAuthorFilter, TestUpdateBook, TestDeleteBook, TestNotFoundAndBadIDs,
TestDuplicateISBNConflict, TestPersistenceAcrossReopen, TestValidISBN
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go, source only) | ~600 (main+handlers+store) |
| Lines of code (tests) | ~396 (api_test.go) |
| Files | 15 |
| Dependencies (go.sum lines) | 20 |
| Tests total | 10 funcs |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] Validation failures return 422, spec R9 names 400 — `handlers.go:82`
2. [info] run-summary skill unavailable; architecture summary not generated

## Reproduce

```bash
cd "experiments/adrianco/experiment-65-fable51-effort/rest-api-crud/runs/effort=default_language=go_model=claude-fable-5-1_prompt=neutral/rep1"
cat scores.json
grep -cE '^func Test' api_test.go
grep -rnE 't\.Skip' . --include='*.go' | wc -l
go test ./...   # optional re-verify
```
