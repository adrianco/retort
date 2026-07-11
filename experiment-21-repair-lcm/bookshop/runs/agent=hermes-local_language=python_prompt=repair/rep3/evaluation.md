# Evaluation: agent=hermes-local language=python prompt=repair · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), framework=Flask, prompt=repair
- **Status:** ok — repair succeeded (prior attempt was `failed`: had `app.py` but no tests/README)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (+1 prompt instruction P1 satisfied)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — `defect_rate=1.0` from scores.json (build + tests executed)
- **Lint:** pass — `code_quality=0.789` from scores.json (no warnings surfaced by the scorer)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:67 create_book` inserts 4 fields; `test_app.py:52 test_create_book` (201) |
| R2 | GET /books lists all | ✓ implemented | `app.py:111 list_books`; `test_app.py:90 test_list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:117-121` `WHERE author LIKE ?`; `test_app.py:103 test_list_books_author_filter` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:142 get_book` returns 404; `test_app.py:118 test_get_book` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:166 update_book`; `test_app.py:137/152` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:211 delete_book`; `test_app.py:161/176` |
| R7 | SQLite persistence | ✓ implemented | `app.py:15 sqlite3.connect`, `books.db`; not in-memory |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` + 201/200/400/404/409 throughout `app.py` |
| R9 | Validate title & author required | ✓ implemented | `app.py:77-80` 400 on blank; `test_app.py:68/78` |
| R10 | GET /health | ✓ implemented | `app.py:57 health` → `{status: ok}` 200; `test_app.py:184 test_health` |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, test, curl examples |
| R12 | ≥ 3 tests | ✓ implemented | `test_app.py` has 11 tests; `test_coverage=0.93` |
| P1 | Repair (don't restart, keep layout) | ✓ implemented | Kept existing `app.py`; added `test_app.py`, `README.md`, `DATABASE_PATH` env-var (`_agent_stdout.log`) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline eval gate):

```text
scores.json
  test_coverage = 0.93   (tests ran and passed; coverage-based)
  defect_rate   = 1.0    (build + tests executed successfully)
  code_quality  = 0.789
  maintainability = 0.985
  idiomatic     = 0.68
  token_efficiency = 0.0135
```

```text
_agent_stdout.log: "All 11 tests pass."
skip scan (pytest.skip/mark.skip/xfail on test_app.py): 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 420 (app.py 231, test_app.py 189) |
| Files (excl. __pycache__/.coverage) | 14 (2 source: app.py, test_app.py) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores cached) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] `init_db()` runs on every request via `before_request` — `app.py:47-50`
2. [low] PUT only validates year type when the value changes — `app.py:189`
3. [info] ISBN uniqueness enforced with 409 (beyond spec) — `app.py:39`
4. [info] Very low token efficiency (0.0135) for a small 2-file repair — 430,943 tokens / 15 API calls

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-21-repair-lcm/bookshop/runs/agent=hermes-local_language=python_prompt=repair/rep3
cat scores.json                       # cached mechanical scores (build/test/lint)
pip install -r requirements.txt       # flask, pytest
pytest test_app.py -v                 # 11 tests, all pass
grep -nE "@app.route" app.py          # 6 routes
```
