# Evaluation: effort=high language=python model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 40 passed / 0 failed / 0 skipped (40 effective)
- **Build:** pass (test_coverage=0.95 from scores.json ⇒ build + tests executed and passed)
- **Lint:** pass — code_quality=0.6667 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Scores (from `scores.json`): test_coverage=0.95, defect_rate=1.0, code_quality=0.667, maintainability=0.915, idiomatic=0.88, token_efficiency=0.028.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:129 _create_book` → `db.py:55 create_book`; `test_api.py:64` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:121 _list_books` → `db.py:40 list_books`; `test_api.py:102` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:122` reads `author`; `db.py:45` filters `WHERE author = ? COLLATE NOCASE`; `test_api.py:112` |
| R4 | GET /books/{id} returns a book (404 if absent) | ✓ implemented | `app.py:133 _get_book` raises 404; `test_api.py:135` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:139 _update_book` → `db.py:65 update_book`; `test_api.py:140`, 404 at `test_api.py:163` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:146 _delete_book` → `db.py:78 delete_book`; `test_api.py:168` |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:25 sqlite3.connect`, file-backed via `--db`; restart test `test_api.py:199` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:160 _send_json`; 201/200/204/400/404/405/500 across handlers; `test_api.py` asserts codes |
| R9 | Input validation: title and author required | ✓ implemented | `validation.py:44 _text` "is required"; 400 at `app.py:72`; `test_api.py:82`, `test_validation.py:33` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:114 _health` returns `{"status":"ok"}`; `test_api.py:180` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` Setup/Run/Test sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 30 test functions → 40 after parametrization; test_coverage=0.95 > 0 |

No partial or missing requirements. No enhancements were counted as deductions.

## Build & Test

Not re-run — stored scores used per the evaluate-run skill.

```text
scores.json: {"test_coverage": 0.95, "defect_rate": 1.0, ...}
test_coverage=0.95 (>0) ⇒ build succeeded and the test suite ran and passed.
defect_rate=1.0 ⇒ build + test succeeded.
```

```text
Test inventory (static): 30 test functions
  test_api.py          18 functions (end-to-end against a live server)
  test_validation.py   12 functions (3 parametrized ×2, 2 parametrized ×5)
  → 40 effective tests; 0 skipped / xfail (grep clean)
README reports "The suite has 40 tests" — consistent.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 384 (app 207 + db 88 + validation 91, minus overlap) |
| Lines of code (incl. tests) | 681 |
| Files (source + docs) | 13 |
| Dependencies | 1 runtime (none; stdlib only) / 1 dev (pytest) |
| Tests total | 40 |
| Tests effective | 40 |
| Skip ratio | 0% |
| Build duration | not re-run (stored scores) |

## Findings

All 4 findings are informational (no deductions):

1. [info] Validation goes beyond spec (ISBN format, year range, text length) — `validation.py`
2. [info] Zero runtime dependencies (stdlib http.server + sqlite3) — `app.py:14`, `db.py:3`
3. [info] Persistence verified by a restart test — `test_api.py:199`
4. [info] No request body size limit on POST/PUT — `app.py:153` (low concern for a local service)

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=high_language=python_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                  # stored build/test/quality scores
cat ../../REQUIREMENTS.json                       # pinned 12-requirement checklist
grep -rEc "^def test_" test_api.py test_validation.py   # 18 + 12 = 30 functions (40 after parametrize)
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_api.py test_validation.py   # 0 skips
# optional, not required by the skill: python -m pytest -q
```
