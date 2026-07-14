# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s1 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask), prompt=none, stack=s1
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.7888` (scores.json); no blocking warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:60 create_book` — inserts title/author/year/isbn, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:100 list_books` — returns collection, 200 |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:107-111` — `WHERE author LIKE %?%`; `test_list_books_filter_by_author` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:118 get_book` — 200 / 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:130 update_book` — partial update, 200 / 404 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:175 delete_book` — 200 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,13,27-40` — sqlite3, `books` table in `books.db` |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify(...)` throughout with 201/200/400/404 |
| R9 | title & author required | ✓ implemented | `app.py:74-78` — 400 on missing/empty; `test_create_book_missing_title/author` |
| R10 | GET /health | ✓ implemented | `app.py:54 health_check` — `{"status":"healthy"}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, endpoints, test instructions |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 16 tests, `test_coverage=0.98` |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.98   # tests executed, all pass; 98% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7888
maintainability = 0.9943
idiomatic     = 0.78
```

```text
python -m pytest test_app.py -v   (16 tests; per _agent_stdout.log: "16/16 passed")
0 skipped, 0 xfail (grep for pytest.skip/xfail → none)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 436 (app.py 192 + test_app.py 244) |
| Files (source) | 5 (app.py, test_app.py, requirements.txt, README.md, stack.json) |
| Dependencies | 2 (flask>=3.0, pytest>=7.0) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — none at or above medium:

1. [low] `init_db()` only runs under `__main__`, so a WSGI/gunicorn deploy never creates the table (`app.py:190-192`)
2. [info] Year validation (0–2100) added beyond spec (`app.py:81-87`) — enhancement
3. [info] `?author=` filter uses substring LIKE match rather than exact equality (`app.py:108-111`) — enhancement

## Reproduce

```bash
cd "experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s1/rep1"
cat scores.json                       # stored mechanical scores
cat ../../../REQUIREMENTS.json        # pinned 12-item checklist
grep -cE "^def test_" test_app.py     # 16 tests
grep -rnE "pytest\.skip|xfail" .      # 0 skips
python -m pytest test_app.py -v       # (optional) re-run: 16 pass
```
