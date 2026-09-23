# Evaluation: agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — `python -m py_compile` succeeded (from `_agent_stdout.log` item_9); test_coverage=0.88, defect_rate=1.0 from scores.json
- **Lint:** n/a — no linter run; code_quality=0.79 (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:86-93` INSERT + 201; test `test_create_get_update_delete_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:77-85` SELECT * ORDER BY id; exercised in filter test |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:78,82-84`; test `test_list_filters_by_author` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:101-105`; test asserts 404 after delete |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:106-115`; test updates title to "Dune Messiah" |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:116-121` returns 204; test asserts 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `app.py:13-25` sqlite3 + CREATE TABLE books |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:127-131`; 201/204/404/400/405 used |
| R9 | Validation: title & author required | ✓ implemented | `app.py:38-52`; test asserts 400 + "author" error |
| R10 | GET /health | ✓ implemented | `app.py:75-76`; test asserts `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md:9-15,38-40` run + test instructions |
| R12 | >= 3 tests | ✓ implemented | `test_app.py` — 3 test methods; test_coverage=0.88 |

## Build & Test

```text
python -m unittest -v   (from _agent_stdout.log item_9)
test_create_get_update_delete_book ... ok
test_list_filters_by_author ... ok
test_required_fields_and_health ... ok
----------------------------------------------------------------------
Ran 3 tests in 0.004s
OK
```

Mechanical scores read from `scores.json` (inline gate; DB row not queried — not present for this replicate):
test_coverage=0.88, defect_rate=1.0, code_quality=0.79, maintainability=0.91, idiomatic=0.78.

Note: the agent's *final* verification command bundle was rejected by codex's own sandbox
(`_agent_stderr.log`: "rm -f style commands are not permitted") because it chained `rm -rf __pycache__`.
This is a harness rejection of the cleanup step only — the test run had already passed twice
(items 6 and 9) before it, so it has no effect on the scores.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 145 (app.py) + 61 (test_app.py) = 206 |
| Files | 3 (app.py, test_app.py, README.md) |
| Dependencies | 0 (stdlib only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (compile + unittest ~0.004s test time) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Health check is static and does not verify DB connectivity (`app.py:75-76`)
2. [info] PUT uses full-replace semantics; title+author always required (`app.py:106-115`)

No missing/partial requirements, no skipped tests, no build/test failures.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep1
cat scores.json
python -m unittest -v          # 3 tests, all pass
grep -cE 'def test_' test_app.py
```
