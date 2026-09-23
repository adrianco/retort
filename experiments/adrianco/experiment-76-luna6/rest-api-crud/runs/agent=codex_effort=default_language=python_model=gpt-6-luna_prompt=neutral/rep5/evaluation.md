# Evaluation: agent=codex effort=default language=python model=gpt-6-luna prompt=neutral · rep 5

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, framework=unknown, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from scores.json (defect_rate=1.0)
- **Lint:** pass — code_quality=0.7889 (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:70-81` INSERT of all four fields |
| R2 | GET /books lists all books | ✓ implemented | `app.py:64-68` SELECT * ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:65-67` `(? IS NULL OR author = ?)`; test `test_app.py:45` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:86-89`; test `test_app.py:48` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:90-104`; test `test_app.py:52` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:105-110`; test `test_app.py:55` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:18-30` sqlite3 + CREATE TABLE books |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:41-45` respond(); 201/200/404/400/204 used |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:75-76`, `99-100`; test `test_app.py:42` (400) |
| R10 | GET /health endpoint | ✓ implemented | `app.py:61-62` `{"status":"ok"}`; test `test_app.py:57` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` (run, endpoints, tests) |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` 3 methods; test_coverage=0.91 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output).

```text
scores.json: {"code_quality": 0.7889, "token_efficiency": 0.0104, "test_coverage": 0.91,
              "defect_rate": 1.0, "maintainability": 0.9848, "idiomatic": 0.7}
```

- `defect_rate=1.0` ⇒ build + tests succeeded.
- `test_coverage=0.91` ⇒ tests executed and passed (0.91 coverage).
- 3 test methods, 0 skips (`grep` for `unittest.skip`/`pytest.skip`/`xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 185 (app.py 124 + test_app.py 61) |
| Files | 4 (app.py, test_app.py, README.md, TASK.md) |
| Dependencies | 0 (stdlib only — no requirements.txt/pyproject.toml) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] New SQLite connection opened per request — `app.py:66,77,87,94,106`
2. [info] GET /books has no pagination (not required by spec) — `app.py:64-68`

## Reproduce

```bash
cd "experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep5"
cat scores.json                                   # mechanical scores (build/test/lint)
grep -rEn "def test_" test_app.py                 # 3 tests
grep -rEn "unittest\.skip|pytest\.skip|xfail" *.py # 0 skips
python -m unittest -v                             # optional: re-run tests
```
