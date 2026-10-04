# Evaluation: rest-api-crud · effort=high language=python model=claude-opus-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=high (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 37 passed / 0 failed / 0 skipped (37 effective) — via `test_coverage=0.97`, `defect_rate=1.0`
- **Build:** pass (from `scores.json`; not re-run)
- **Lint:** pass — `code_quality=0.8333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:140 _create_book` → `store.py:48 create`; `test_api.py:test_create_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:134 _list_books` → `store.py:57 list`; `test_list_books_returns_all_in_creation_order` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:137`; `store.py:61 WHERE author = ? COLLATE NOCASE`; `test_list_books_filters_by_author` |
| R4 | GET /books/{id} + 404 | ✓ implemented | `app.py:144 _get_book`; `test_get_book`, `test_get_missing_book` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:150 _update_book` → `store.py:73 update`; `test_update_book` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:156 _delete_book` → `store.py:87 delete`; `test_delete_book` |
| R7 | Stored in SQLite | ✓ implemented | `store.py:34 sqlite3.connect`; schema `store.py:10` |
| R8 | JSON + HTTP status codes | ✓ implemented | `app.py:66-72` JSON encode; 201/200/204/400/404/405/500 across handlers |
| R9 | Validation: title+author required | ✓ implemented | `validation.py:24-28`; `test_create_book_rejects_invalid_fields`, `..._reports_every_invalid_field` |
| R10 | GET /health | ✓ implemented | `app.py:124 _health` (pings DB); `test_health`, `test_health_reports_unusable_database` |
| R11 | README with setup+run | ✓ implemented | `README.md` Setup/Run/endpoint sections |
| R12 | ≥3 tests that run | ✓ implemented | 37 test functions across 3 files; `test_coverage=0.97` |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill step 2):

```text
{"code_quality": 0.833, "token_efficiency": 0.036, "test_coverage": 0.97,
 "defect_rate": 1.0, "maintainability": 0.903, "idiomatic": 0.77}
```

`test_coverage=0.97` and `defect_rate=1.0` ⇒ build succeeded and all tests passed. Skip scan (`pytest.skip|mark.skip|xfail`) over `tests/` returned 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Python, src+tests) | 975 |
| Files (src+tests) | 10 |
| Dependencies (runtime) | 0 (pytest dev-only) |
| Tests total | 37 |
| Tests effective | 37 |
| Skip ratio | 0% |
| Build duration | n/a (scores read, not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level enhancements, no defects:

1. [info] Zero runtime dependencies — pure stdlib WSGI + sqlite3
2. [info] Defensive request handling beyond spec (1MiB body cap, HEAD, 405 Allow, 500 without leak)
3. [info] SQL-injection-safe author filter with dedicated regression test

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=high_language=python_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                                         # mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json                          # pinned 12-item checklist
grep -rhE "def test_" tests/ | wc -l                    # 37 test functions
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/  # 0 skips
find src tests -name '*.py' | xargs wc -l | tail -1     # 975 LOC
```
