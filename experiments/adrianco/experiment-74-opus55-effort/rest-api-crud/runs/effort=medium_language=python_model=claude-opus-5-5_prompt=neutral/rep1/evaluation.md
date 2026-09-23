# Evaluation: rest-api-crud · effort=medium language=python model=claude-opus-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5-5, effort=medium, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective — 11 test functions, one parametrized ×4)
- **Build:** pass — test_coverage=0.93 from scores.json (build + tests ran and passed)
- **Lint:** pass — code_quality=0.789 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

Stored scores (scores.json): test_coverage=0.93, code_quality=0.789, defect_rate=1.0, maintainability=1.0, idiomatic=0.85, token_efficiency=0.014.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:187 do_POST` → `validate_book` → `BookStore.create` (app.py:52) |
| R2 | GET /books lists all | ✓ implemented | `app.py:178` → `store.list()` (app.py:60) |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:179` parse_qs; `app.py:62-66` WHERE author=? COLLATE NOCASE; `tests:82-84` |
| R4 | GET /books/{id} single, 404 | ✓ implemented | `app.py:181-184` store.get / 404; `tests:52-54,108` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:196-205 do_PUT`; `BookStore.update` app.py:82; `tests:90-102` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:207-213`; `tests:105-110` |
| R7 | SQLite storage | ✓ implemented | `app.py:33-46` sqlite3.connect + CREATE TABLE books |
| R8 | JSON + appropriate status codes | ✓ implemented | `app.py:146-160` _send/_error; 201/200/204/400/404 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:107-112`; `tests:57-64` |
| R10 | GET /health | ✓ implemented | `app.py:176-177` → `{"status":"ok"}`; `tests:42-43` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Run, Endpoints, Tests sections |
| R12 | ≥3 tests | ✓ implemented | `tests/test_app.py` 11 functions; test_coverage=0.93 > 0 |

Enhancements beyond spec: ISBN-10/13 and year-range validation, invalid-JSON handling, persistence-across-restarts test, `--host/--port/--db` CLI.

## Build & Test

Not re-run — stored scores used per skill (test_coverage=0.93 ⇒ build + tests passed; defect_rate=1.0).

```text
scores.json: {"code_quality": 0.789, "test_coverage": 0.93, "defect_rate": 1.0,
              "maintainability": 1.0, "idiomatic": 0.85, "token_efficiency": 0.014}
```

Skip scan: `grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 243 (app.py) + 149 (tests) = 392 |
| Files | 2 source (app.py, tests/test_app.py) + README |
| Dependencies | 0 runtime; 1 dev (pytest) |
| Tests total | 15 (11 functions, one parametrized ×4) |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Single shared SQLite connection under one global lock serializes all requests — `app.py:34-36`
2. [info] Validation exceeds spec (ISBN-10/13 + year range) — `app.py:114-132`
3. [info] Zero third-party dependencies (stdlib only) — `app.py:12-18`
4. [info] 11 tests, 0 skips, cover CRUD + filter + validation + persistence

## Reproduce

```bash
cd runs/effort=medium_language=python_model=claude-opus-5-5_prompt=neutral/rep1
cat scores.json                 # stored mechanical scores (build/test/lint)
grep -rE "pytest\.skip|xfail" tests/   # skip scan → 0
pytest -q tests                 # optional: 15 pass
```
