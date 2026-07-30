# Evaluation: agent=codex effort=max language=python model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-terra, effort=max, prompt=neutral, framework=Flask (inferred from source)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — from `defect_rate=1.0`, `test_coverage=0.92` in `scores.json`
- **Build:** pass (import/collection succeeded; `defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.7889` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:58` `create_book`; test `make_book` @ `tests/test_app.py:20,38` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:73` `list_books`; `tests/test_app.py:52` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:76-82` WHERE author=?; `tests/test_app.py:60` |
| R4 | GET /books/{id} by id (404 if absent) | ✓ implemented | `app.py:85` `get_book` + `not_found`; `tests/test_app.py:71,96` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:92` `update_book`; `tests/test_app.py:75` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:119` `delete_book` (204 / 404); `tests/test_app.py:93` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:14-22` schema, `sqlite3.connect` @ `app.py:138,147`; default file `books.sqlite3` @ `app.py:29-31` |
| R8 | JSON responses + HTTP status codes | ✓ implemented | `jsonify` throughout; 201 `app.py:71`, 404 `app.py:206`, 400 `app.py:202`, 204 `app.py:126`; HTTPException→JSON `app.py:50-52` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:177-180`; `tests/test_app.py:99-109` |
| R10 | GET /health | ✓ implemented | `app.py:54-56`; `tests/test_app.py:31` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (setup, run, endpoints, tests) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 test functions in `tests/test_app.py` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.92   # tests executed and passed; 92% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.38
```

Skip scan (`grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/`): 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 322 (`app.py` 213 + `tests/test_app.py` 109) |
| Files (source, excl. artifacts) | 4 (`app.py`, `tests/test_app.py`, `README.md`, `requirements.txt`) |
| Dependencies | 2 (`Flask`, `pytest`) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (scores read from `scores.json`) |

## Findings

No high/critical/medium findings. Two informational notes (full list in `findings.jsonl`):

1. [info] Default DB is a persistent SQLite file; tests use an isolated `tmp_path` DB.
2. [info] PUT /books/{id} is a full replace requiring title+author (matches spec).

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=max_language=python_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l
grep -rEn "def test_" tests/ | wc -l
# (optional) run tests yourself:
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python3 -m pytest
```
