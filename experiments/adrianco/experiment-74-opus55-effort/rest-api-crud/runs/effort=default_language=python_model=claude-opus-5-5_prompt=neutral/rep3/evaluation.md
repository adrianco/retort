# Evaluation: effort=default_language=python_model=claude-opus-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-5-5, effort=default, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — 11 test functions, one parametrized ×5
- **Build:** pass — from `defect_rate=1.0` (scores.json); no separate build step (interpreted)
- **Lint:** pass — `code_quality=0.7889` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:218 do_POST` → `BookStore.create` (`app.py:53`); test_create_and_get_book |
| R2 | GET /books lists books | ✓ implemented | `app.py:205` → `store.list`; test_list_and_author_filter |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:61-70` case-insensitive `COLLATE NOCASE`; test_list_and_author_filter |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:208-216` (404 if absent, 400 bad id); test_create_and_get_book, test_not_found_and_bad_ids |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:242 do_PUT` → `store.update`; test_update_book |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:263 do_DELETE` → `store.delete`; test_delete_book |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:34-47` sqlite3, file-backed default `books.db`; test_persists_across_restarts |
| R8 | JSON responses + status codes | ✓ implemented | `_send`/`_error` (`app.py:154-168`); 201/200/204/400/404/405/422 across handlers |
| R9 | Validation: title+author required | ✓ implemented | `validate_book` (`app.py:99-143`); test_create_requires_title_and_author (returns 422 — see finding R9-code) |
| R10 | GET /health | ✓ implemented | `app.py:203-204` → `{"status":"ok"}`; test_health |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, env vars, endpoints, examples, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 11 functions / 15 effective cases; test_coverage=0.92 |

No prompt-factor requirements: `prompts/neutral.md` prescribes no methodology beyond "include tests," covered by R12.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=0.92  defect_rate=1.0  code_quality=0.7889
             maintainability=0.9922  idiomatic=0.8  token_efficiency=0.0148
# defect_rate=1.0 ⇒ build + tests succeeded; coverage 92%.
```

```text
# Test inventory (grep, not executed here)
test_app.py: 11 test functions; test_create_rejects_bad_fields parametrized ×5 = 15 effective cases
skips/xfail: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 302 (app.py) + 168 (test_app.py) = 470 |
| Files | 13 (incl. .coverage, caches, logs); 3 source/doc: app.py, test_app.py, README.md |
| Dependencies | 1 (pytest, test-only; runtime = stdlib only) |
| Tests total | 15 effective cases (11 functions) |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (interpreted; not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational:

1. [info] Validation failures return 422 while the pinned how_to_verify cites 400 (RFC-valid; R9 still satisfied)
2. [info] Line coverage 0.92, not 1.0 (uncovered: `main()`, oversized-body and bad Content-Length guards)
3. [info] ISBN-10/13 shape validation + unknown-field rejection beyond spec
4. [info] Zero-dependency stdlib implementation; thread-safe SQLite store

## Reproduce

```bash
cd "experiments/adrianco/experiment-74-opus55-effort/rest-api-crud/runs/effort=default_language=python_model=claude-opus-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores
grep -cE "^def test_" test_app.py                 # test function count
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # skips = 0
# Optional live re-run:
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && pytest -q
```
