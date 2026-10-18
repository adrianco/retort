# Evaluation: effort=low_language=c_model=claude-haiku-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 85 checks across 9 test functions passed / 0 failed / 0 skipped (85 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass (code_quality=1.0 from scores.json; builds under `-Wall -Wextra -Werror`)
- **Architecture:** summary skill unavailable in this session — see module notes below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Scores read from `scores.json` (inline gate output): `test_coverage=1.0`, `code_quality=1.0`,
`defect_rate=1.0`, `maintainability=0.634`, `idiomatic=0.4`, `token_efficiency=0.040`.
Build/tests NOT re-run per the skill (stored scores authoritative).

## Requirements

Checklist pinned from `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/router.c:create_book` → `book_create` INSERT `src/store.c:78`; test `test_create_and_get` |
| R2 | GET /books lists all | ✓ implemented | `src/router.c:list_books` → `book_list` `src/store.c:138`; test `test_list_and_author_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `query_param` `src/router.c:131` + `WHERE author = ?1 COLLATE NOCASE` `src/store.c:141` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `src/router.c:get_book` returns 404 on NOT_FOUND; test asserts 404 for /books/999 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/router.c:update_book` → `book_update` `src/store.c:103`; test `test_update` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/router.c:delete_book` → `book_delete`; 204 No Content; test `test_delete` |
| R7 | Data stored in SQLite | ✓ implemented | `src/store.c` uses sqlite3; `test_persistence_across_reopen` proves on-disk persistence |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/204/400/404/405/409 across `src/router.c`; `Content-Type: application/json` `src/http.c:75` |
| R9 | Validation: title & author required | ✓ implemented | `book_from_json` `src/router.c:72` → 400; test `test_validation` (11 bad inputs) |
| R10 | GET /health | ✓ implemented | `src/router.c:router_handle` → `{"status":"ok"}`; test `test_routing` |
| R11 | README with setup/run | ✓ implemented | `README.md` — requirements, build/run/test, env vars, API reference |
| R12 | ≥3 tests | ✓ implemented | 9 test functions / 85 checks in `tests/test_api.c`; test_coverage=1.0 |

## Build & Test

Not re-run — stored scores used per evaluate-run step 2.

```text
scores.json: test_coverage=1.0  ⇒ `make test` built and all 85 checks passed
scores.json: code_quality=1.0   ⇒ compiles clean under -std=gnu11 -Wall -Wextra -Werror
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, src/ + tests/) | 1627 |
| Files (excl. build artifacts/logs/binary) | 20 |
| Dependencies | 1 (sqlite3, system lib via pkg-config) |
| Tests total | 85 checks / 9 functions |
| Tests effective | 85 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl`. No correctness, build, test, or requirement defects.

1. [info] Implements features beyond the spec (409 on duplicate ISBN, 405 handling, URL-decoded filter)
2. [info] HTTP layer hardened against malformed/oversized requests (size caps, TE rejection, read timeout)

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=c_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                       # stored build/test/lint scores (not re-run)
cat ../../../REQUIREMENTS.json        # pinned 12-item checklist
make test                             # optional: rebuild + run 85 checks (expects sqlite3 dev headers)
grep -rniE "SKIP|#if 0|TODO|FIXME" src tests   # confirm no disabled tests (only skip_ws matches)
```
