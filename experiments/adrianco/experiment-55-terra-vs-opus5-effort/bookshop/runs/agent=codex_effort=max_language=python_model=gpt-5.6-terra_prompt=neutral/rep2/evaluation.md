# Evaluation: agent=codex_effort=max_language=python_model=gpt-5.6-terra_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-terra, effort=max, prompt=neutral, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — 5 test functions, one parametrized ×3
- **Build:** pass — from `test_coverage=0.95`, `defect_rate=1.0` in scores.json (tests ran + passed)
- **Lint:** pass — `code_quality=0.7888` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

Clean run. Every pinned requirement is satisfied with test evidence; the mechanical
scores (`test_coverage=0.95`, `defect_rate=1.0`, `maintainability=1.0`, `idiomatic=0.85`)
confirm build + tests passed.

## Requirements

Denominator is the pinned `REQUIREMENTS.json` (12 items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:53 create_book` inserts title/author/year/isbn; `test_api.py:35` asserts 201 + body |
| R2 | GET /books lists all | ✓ implemented | `app.py:69 list_books`; `test_api.py:85` lists ids [1,2,3] |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:78-88` WHERE author COLLATE NOCASE; `test_api.py:89` filters |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:91 read_book`, 404 if absent; `test_api.py:48,69` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:98 update_book`; `test_api.py:52` asserts updated fields |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:127 delete_book` → 204; `test_api.py:65` |
| R7 | Data stored in SQLite | ✓ implemented | stdlib `sqlite3` throughout; `SCHEMA` at `app.py:13`, `init_db` at `app.py:173` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/204/405 returned; 404 & 405 error handlers `app.py:138-144` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:216 required_text` → 400; `test_api.py:97` parametrized cases |
| R10 | GET /health | ✓ implemented | `app.py:49 health` → `{"status":"ok"}`; `test_api.py:28` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Run, API table, curl example, Tests |
| R12 | ≥ 3 tests | ✓ implemented | `tests/test_api.py` — 5 functions / 7 effective cases; `test_coverage=0.95` |

Enhancement beyond spec (not deductions): app-factory pattern with injectable DB
config, `BOOKS_DATABASE` env override, case-insensitive author filter, JSON 405
handler, strict `year` bool/range validation.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
test_coverage = 0.95   # tests executed and passed (coverage 95%)
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7889 # lint/quality
maintainability = 1.0
idiomatic     = 0.85
```

```text
pytest (testpaths=tests, pythonpath=.)
5 test functions; test_book_payload_validation parametrized ×3 → 7 effective cases
0 skips / 0 xfail
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source) | 251 (app.py) + 122 (tests) = 373 |
| Files | 4 (app.py, tests/test_api.py, README.md, requirements.txt) + configs |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 7 effective cases (5 functions) |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (scores read from cache) |

## Findings

None. `findings.jsonl` is empty — no missing/partial requirements, no skipped
tests, no build/test failures.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=max_language=python_model=gpt-5.6-terra_prompt=neutral/rep2"
cat scores.json          # mechanical scores (no re-run needed)
python -m pip install -r requirements.txt
pytest                   # 7 effective cases, all pass
```
