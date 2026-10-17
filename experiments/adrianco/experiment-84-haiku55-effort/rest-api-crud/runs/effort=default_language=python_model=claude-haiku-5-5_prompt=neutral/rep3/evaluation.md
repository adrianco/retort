# Evaluation: effort=default_language=python_model=claude-haiku-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=default, prompt=neutral (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all passing / 0 failed / 0 skipped (test_coverage=1.0 gate, 0.92 line coverage; defect_rate=1.0 from retort.db)
- **Build:** pass (not re-run — test_coverage=1.0 from retort.db)
- **Lint:** pass — code_quality=0.6667 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

All requirement verdicts come from the stored scores (no build/test/lint re-run per the skill) plus source inspection. Pinned checklist `REQUIREMENTS.json` (12 requirements) used verbatim.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `http_app.py:118 _create_book` → `store.py:42 create`; test_api.py:55 |
| R2 | GET /books lists all books | ✓ implemented | `http_app.py:114 _list_books` → `store.py:54 list`; test_api.py:74 |
| R3 | GET /books supports ?author= filter | ✓ implemented | `http_app.py:115` reads `author` query; `store.py:60` filters; test_api.py:83 |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `http_app.py:123 _get_book`; test_api.py:63, test_api.py:108 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `http_app.py:129 _update_book` → `store.py:66 update`; test_api.py:91 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `http_app.py:137 _delete_book` → `store.py:77 delete`; test_api.py:99 |
| R7 | Data stored in SQLite | ✓ implemented | `store.py:3,27 sqlite3.connect`; test_store.py:19 persists across connections |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `http_app.py:177 _send_json`; 201/200/204/400/404/405/413/500 used throughout |
| R9 | Input validation: title & author required | ✓ implemented | `validation.py:28-29 _required_text`; test_api.py:119, test_validation.py |
| R10 | GET /health endpoint | ✓ implemented | `http_app.py:105 _health` (pings DB); test_api.py:49 |
| R11 | README.md with setup & run instructions | ✓ implemented | `README.md` Setup/Run/Test sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 3 test files, ~26 functions (parametrized to ~48 cases); test_coverage=1.0 |

No prompt-factor requirements (prompt=neutral is a tone instruction, no extra checkable asks).

## Build & Test

Not re-run — stored scores used per the evaluate-run skill:

```text
# from retort.db (run_id for python/claude-haiku-5-5/rep3, status=completed)
test_coverage = 1.0        # build + all tests passed (gate); scores.json reports 0.92 line coverage
defect_rate   = 1.0        # build+test succeeded
code_quality  = 0.6667
maintainability = 0.964
idiomatic     = 0.88
requirement_coverage = 1.0
```

Skip scan: `grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/` → 0 matches. No skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 424 (bookapi/*.py) |
| Lines of code (tests) | 289 (tests/*.py) |
| Files (excl. .git/pycache) | 19 (incl. archive logs/db) |
| Source + test modules | 5 source, 3 test |
| Dependencies | 0 runtime (stdlib only); pytest for tests |
| Tests total | ~26 functions / ~48 parametrized cases |
| Tests effective | all (0 skipped) |
| Skip ratio | 0% |

## Findings

All 3 findings are `info` (beyond-spec notes, not defects) — full list in `findings.jsonl`:

1. [info] `?author=` filter is exact case-insensitive match, not substring (`store.py:60`)
2. [info] PUT /books/{id} is a full replace requiring title+author (`http_app.py:129`)
3. [info] year validation constrains range to 1..next-year beyond spec (`validation.py:63`)

No build, test, requirement, security, or skipped-test issues. This is a clean, complete pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=default_language=python_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                  # stored mechanical scores
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ | wc -l   # skip scan -> 0
# stored scores cross-check (read-only):
db=../../../retort.db
sqlite3 -readonly "$db" "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id=(SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='python' AND json_extract(er.run_config_json,'\$.model')='claude-haiku-5-5' AND er.replicate=3 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
```
