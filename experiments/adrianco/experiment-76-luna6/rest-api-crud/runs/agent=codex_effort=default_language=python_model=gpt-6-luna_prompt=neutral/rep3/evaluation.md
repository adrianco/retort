# Evaluation: agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — import/collection succeeded (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.79 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 0 low, 1 info)

## Requirements

Pinned checklist from `REQUIREMENTS.json` (12 fixed requirements, used verbatim).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:93-109` do_POST validates + INSERT, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:71-80` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:72,77-79` filters `WHERE author = ?` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:82-91` 404 on missing id |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:111-131` UPDATE, 404 on rowcount 0 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:133-143` DELETE, 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:17-28` sqlite3 books table |
| R8 | JSON responses + correct status codes | ✓ implemented | `app.py:39-49` `_send`; 201/200/204/400/404 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:156-170` `_validate` rejects empty title/author (400) |
| R10 | GET /health | ✓ implemented | `app.py:68-69` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md:1-40` run + endpoints + tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 3 tests; test_coverage=0.41 (>0) |

Prompt factor `neutral` is methodology guidance only ("include tests that demonstrate the implementation meets the requirements") — no additional checkable P-requirements beyond R12.

## Build & Test

Scores read from `scores.json` (inline gate; run not yet in `retort.db`) — build/tests not re-run per skill guidance.

```text
scores.json
test_coverage = 0.41   (tests executed; build+import OK)
defect_rate   = 1.0    (build+test succeeded)
code_quality  = 0.79
maintainability = 0.80
idiomatic     = 0.87
```

```text
python3 -m unittest -v   (per README; not re-executed)
3 tests: schema round-trip, required-field validation, optional-field typing
0 skipped (grep for unittest.skip/pytest.skip/xfail = 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 240 (app.py 196 + test_app.py 44) |
| Files | 3 source (app.py, test_app.py, README.md) |
| Dependencies | 0 (stdlib only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Test coverage | 0.41 |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [medium] HTTP route handlers are untested (coverage 0.41) — tests call `_validate`/schema directly; `do_*` dispatch, status codes, and `?author=` filter are never driven.
2. [info] Dependency-free stdlib implementation — only `http.server` + `sqlite3`; trivial setup, minimal supply-chain surface.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep3
cat scores.json                              # stored mechanical scores
cat ../../../REQUIREMENTS.json               # pinned 12-requirement checklist
python3 -m unittest -v                        # 3 tests (per README)
grep -rEc "unittest\.skip|pytest\.skip|xfail" *.py   # skip count = 0
```
