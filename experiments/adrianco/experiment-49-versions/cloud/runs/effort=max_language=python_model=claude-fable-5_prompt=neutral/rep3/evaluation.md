# Evaluation: effort=max_language=python_model=claude-fable-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-fable-5, prompt=neutral, effort=max
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective)
- **Build:** pass (test_coverage=0.98 from scores.json — build + tests executed)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

Using the pinned checklist `cloud/REQUIREMENTS.json` (12 requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:66 create_book` — INSERT of 4 fields; `test_app.py:35` 201 + body |
| R2 | GET /books lists all books | ✓ implemented | `app.py:86 list_books`; `test_app.py:81` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:90-94` `WHERE author=? COLLATE NOCASE`; `test_app.py:93` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:100 get_book` returns 404 on None; `test_app.py:108,115` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:108 update_book`; `test_app.py:121` persisted change |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:129 delete_book` → 204; `test_app.py:151` |
| R7 | Data stored in SQLite | ✓ implemented | `db.py` sqlite3 connection + `books` table schema |
| R8 | JSON responses w/ appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404/405/500 handlers `app.py:155-165` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:34-40 validate_book_payload`; `test_app.py:55,63` |
| R10 | GET /health | ✓ implemented | `app.py:61 health` → `{"status":"ok"}`; `test_app.py:29` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, run, tests, API table, examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_app.py` — 17 tests, 0 skips, test_coverage=0.98 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage = 0.98   (build + tests executed and passed)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.8333
maintainability = 0.8880
idiomatic     = 0.87
```

Test inventory (`grep -cE "^def test_" test_app.py`): 17 tests, 0 skips
(`grep -Ec "pytest.skip|@pytest.mark.skip|xfail"` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 381 (app.py 171, db.py 44, test_app.py 166) |
| Files (source, excl. logs/artifacts) | 7 (app.py, db.py, test_app.py, requirements.txt, README.md, .gitignore, TASK.md) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] All 12 pinned requirements implemented; 17 tests pass with no skips
2. [low] PUT is a full replacement — omitting year/isbn clears them (documented)
3. [low] year is type-checked but not range-validated (not required by spec)

No critical, high, or medium findings. This is a clean, fully spec-conformant run.

## Reproduce

```bash
cd runs/effort=max_language=python_model=claude-fable-5_prompt=neutral/rep3
cat scores.json                                    # mechanical scores (no re-run)
grep -cE "^def test_" test_app.py                  # 17
grep -Ec "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # 0
wc -l app.py db.py test_app.py                     # 381 total
```
