# Evaluation: effort=default language=python model=claude-sonnet-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — from `test_coverage=0.95`, `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.79` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:120-127` POST branch → `Store.create` `app.py:27` |
| R2 | GET /books lists all | ✓ implemented | `app.py:117-119` → `Store.list` `app.py:43` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:118` parses `author`; `Store.list` `app.py:45-47`; test `test_app.py:54` |
| R4 | GET /books/{id} single (404 absent) | ✓ implemented | `app.py:132-133`, 404 at `app.py:148-149` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:134-141` → `Store.update` `app.py:52` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:142-145` → `Store.delete` `app.py:60` |
| R7 | SQLite / embedded storage | ✓ implemented | `sqlite3` `Store` `app.py:14-25`; `__main__` DB_PATH=`books.db` `app.py:168` |
| R8 | JSON responses + correct codes | ✓ implemented | `_send` `app.py:96-102`; 201/200/204/400/404/405/422 across `_route` |
| R9 | Validation: title+author required | ✓ implemented | `validate` `app.py:65-87`; rejected at `app.py:126` (422); tests `test_app.py:46-51` |
| R10 | GET /health | ✓ implemented | `app.py:114-115` → `{"status":"ok"}`; test `test_app.py:36` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run/Endpoints/Test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 7 tests in `test_app.py`; `test_coverage=0.95` |

## Build & Test

Scores read from `scores.json` (run scored inline as a gate; not re-run per skill policy):

```text
test_coverage = 0.95   # build + tests executed and passed (coverage 95%)
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7889 # lint/quality
maintainability = 0.9167
idiomatic     = 0.62
```

Test suite (`test_app.py`): 7 tests — health, create+get, validation, list+author filter,
update, delete, unknown-route. Each spins a real `ThreadingHTTPServer` on an ephemeral
port (`make_server(port=0)`) and exercises it over HTTP. 0 skips / 0 xfail.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 253 (app.py 174 + test_app.py 79) |
| Files (source/doc) | 3 (app.py, test_app.py, README.md) |
| Runtime dependencies | 0 (stdlib only); pytest dev-only |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=0.95) |

## Findings

Top findings (full list in `findings.jsonl`) — none at or above `low`:

1. [info] R9 — validation returns 422 rather than the 400 hinted in the spec (semantically appropriate, documented in README).
2. [info] R8 — full JSON status-code coverage including 405/204 (exceeds spec minimum).

## Reproduce

```bash
cd "$(git rev-parse --show-toplevel)/experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=default_language=python_model=claude-sonnet-5-5_prompt=neutral/rep3"
cat scores.json                      # stored mechanical scores (do not re-run toolchain)
grep -rEn "pytest\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
# optional independent check:
python -m pytest test_app.py -q
```
