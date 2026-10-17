# Evaluation: effort=low language=go model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 test functions (+ 5 subtests) passed / 0 failed / 0 skipped (effective = all)
- **Build:** pass — from `defect_rate=1.0` (scores.json); not re-run
- **Lint:** pass — `code_quality=1.0` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Stored scores (`scores.json`): `test_coverage=0.706` (coverage fraction; tests executed and passed since `defect_rate=1.0`), `code_quality=1.0`, `maintainability=0.867`, `idiomatic=0.85`, `token_efficiency=0.0415`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `api.go:23,40` handleCreate → `store.go:49` Create (201 + Location) |
| R2 | GET /books lists all books | ✓ implemented | `api.go:24,54` handleList → `store.go:81` List |
| R3 | GET /books ?author= filter | ✓ implemented | `api.go:55` reads `author` query; `store.go:84` `WHERE author = ? COLLATE NOCASE`; test `api_test.go:123` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `api.go:25,63` handleGet; `store.go:70` ErrNotFound → 404 `api.go:141` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `api.go:26,76` handleUpdate → `store.go:111` Update (404 if absent) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `api.go:27,93` handleDelete → `store.go:130` Delete (204) |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `store.go:8` `modernc.org/sqlite`; `store.go:16` CREATE TABLE books |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `api.go:157` writeJSON; 201/200/204/400/404/422/500 across handlers |
| R9 | Validation: title and author required | ✓ implemented | `book.go:49` Validate requires title+author; `api.go:115` rejects; test `api_test.go:137`. Returns 422 (checklist `how_to_verify` cites 400) — see findings. |
| R10 | GET /health health check | ✓ implemented | `api.go:22,36` handleHealth → `{"status":"ok"}` 200; test `api_test.go:55` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` setup/run/test/endpoints/examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 6 test funcs in `api_test.go`; `test_coverage=0.706 > 0` |

## Build & Test

Build/test not re-run per skill Step 2 — stored scores used:

```text
defect_rate = 1.0    # build + tests succeeded
code_quality = 1.0   # lint/quality clean
test_coverage = 0.706  # coverage fraction (tests executed & passed)
```

Test inventory (`grep "^func Test" *.go`):

```text
TestHealth
TestBookCRUDLifecycle
TestListAndAuthorFilter
TestCreateValidation            (5 subtests via t.Run)
TestMalformedRequests
TestValidationRejectsUpdateWithoutRequiredFields
skips found: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (go, incl. test) | 648 |
| Files (excl. .git) | 16 |
| Dependencies (go.sum lines) | 50 |
| Tests total | 6 funcs (+5 subtests) |
| Tests effective | all (0 skipped) |
| Skip ratio | 0% |
| Build duration | not re-run (stored score) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R9 validation rejects missing title/author with **422**, while the checklist's `how_to_verify` cites 400 — rejection itself is implemented and tested; 422 is semantically appropriate for validation.
2. [info] Enhancement: ISBN-10/13 shape validation and non-negative year check beyond spec (`book.go:69,57`).
3. [info] Enhancement: graceful shutdown, 1 MiB body cap, SQL-pushed case-insensitive author filter.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=low_language=go_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                                   # stored build/test/lint scores
cat ../../REQUIREMENTS.json                        # pinned 12-item checklist
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rE "^func Test" *.go                          # test inventory
# build/test NOT re-run — defect_rate=1.0 and code_quality=1.0 from scores.json
```
