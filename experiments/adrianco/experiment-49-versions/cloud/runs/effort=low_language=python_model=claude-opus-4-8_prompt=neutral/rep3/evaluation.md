# Evaluation: effort=low_language=python_model=claude-opus-4-8_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-4-8, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — from `scores.json` test_coverage=0.92
- **Build:** pass (test gate — test_coverage=0.92 from scores.json; not re-run)
- **Lint:** pass — code_quality=0.7889 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:103` create_book, INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:120` list_books, returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:123-127` filters by author param |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:132` get_book, 404 on miss |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:142` update_book (full-replace; info note) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:171` delete_book, 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:7,12-30` sqlite3, books.db / :memory: |
| R8 | JSON responses + status codes | ✓ implemented | jsonify throughout; 201/200/204/400/404 |
| R9 | Validation: title+author required | ✓ implemented | `app.py:43-69` _validate, 400 on empty |
| R10 | GET /health | ✓ implemented | `app.py:99-101` returns {"status":"ok"} |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, tests, endpoints |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` 7 tests, test_coverage=0.92 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.92   (build + all tests passed; test gate)
defect_rate   = 1.0    (build+test succeeded)
code_quality  = 0.7889
maintainability = 0.9139
idiomatic     = 0.83
```

```text
python3 -m pytest   # 7 tests, 0 skipped (grep: 0 skip/xfail markers)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 258 (app.py 184 + test_app.py 74) |
| Files | 4 tracked (app.py, test_app.py, requirements.txt, README.md) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (scores read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level, no defects:

1. [info] PUT is full-replace, not partial update — acceptable PUT semantics (`app.py:151`)
2. [info] `year` accepts JSON booleans (bool subclasses int) (`app.py:57`)
3. [info] 7 tests cover all CRUD paths plus 404/validation (exceeds ≥3)

## Reproduce

```bash
cd runs/effort=low_language=python_model=claude-opus-4-8_prompt=neutral/rep3
cat scores.json                                    # stored mechanical scores
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0
python3 -m pytest                                  # optional re-verify: 7 passed
```
